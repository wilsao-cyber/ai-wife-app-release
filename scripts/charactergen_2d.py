"""
CharacterGen 2D Stage - 使用原始 webui.py 的核心邏輯
"""

import sys
import os

CHARACTERGEN_2D = "/home/wilsao6666/ai_wife_app/models/3d/CharacterGen/2D_Stage"
sys.path.insert(0, CHARACTERGEN_2D)

import torch
from PIL import Image
import numpy as np
from pathlib import Path
import json
from torchvision import transforms
from einops import rearrange
from torchvision.utils import save_image

from diffusers import AutoencoderKL, DDIMScheduler
from transformers import (
    CLIPTextModel,
    CLIPTokenizer,
    CLIPImageProcessor,
    CLIPVisionModelWithProjection,
)

from tuneavideo.models.unet_mv2d_condition import UNetMV2DConditionModel
from tuneavideo.models.unet_mv2d_ref import UNetMV2DRefModel
from tuneavideo.models.PoseGuider import PoseGuider
from tuneavideo.pipelines.pipeline_tuneavideo import TuneAVideoPipeline

# ============================
# 配置
# ============================
DEVICE = "cuda:0"
CKPT_DIR = os.path.join(CHARACTERGEN_2D, "load/checkpoint")
IMAGE_ENCODER = os.path.join(CHARACTERGEN_2D, "load/image_encoder")
# 使用 SD 1.5 (不需要授權)
SD_PATH = "sd2-community/stable-diffusion-2-1"
INPUT_IMAGE = "/home/wilsao6666/Pictures/post-image-33571620.jpeg"
OUTPUT_DIR = "/home/wilsao6666/ai_wife_app/output/charactergen_2d"
POSE_JSON = os.path.join(CHARACTERGEN_2D, "material/pose.json")

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

print(f"Device: {DEVICE}")
print(f"Input: {INPUT_IMAGE}")
print(f"Output: {OUTPUT_DIR}")

# ============================
# 載入模型
# ============================
print("\n載入模型...")

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

tokenizer = CLIPTokenizer.from_pretrained(SD_PATH, subfolder="tokenizer")
text_encoder = CLIPTextModel.from_pretrained(SD_PATH, subfolder="text_encoder")
vae = AutoencoderKL.from_pretrained(SD_PATH, subfolder="vae")

# 使用原始 webui.py 的參數
unet = UNetMV2DConditionModel.from_pretrained_2d(
    SD_PATH,
    camera_embedding_type="e_de_da_sincos",
    num_views=4,
    sample_size=96,
    projection_class_embeddings_input_dim=10,
    zero_init_conv_in=False,
    zero_init_camera_projection=False,
    in_channels=4,
    out_channels=4,
    local_crossattn=True,
    subfolder="unet",
)
ref_unet = UNetMV2DRefModel.from_pretrained_2d(
    SD_PATH,
    camera_embedding_type="e_de_da_sincos",
    num_views=4,
    sample_size=96,
    projection_class_embeddings_input_dim=10,
    zero_init_conv_in=False,
    zero_init_camera_projection=False,
    in_channels=4,
    out_channels=4,
    local_crossattn=True,
    subfolder="unet",
)

feature_extractor = CLIPImageProcessor.from_pretrained(IMAGE_ENCODER)
image_encoder = CLIPVisionModelWithProjection.from_pretrained(IMAGE_ENCODER)

noise_scheduler = DDIMScheduler.from_pretrained(SD_PATH, subfolder="scheduler")

# 載入 CharacterGen 權重
print("載入 CharacterGen 權重...")
unet_params = torch.load(
    os.path.join(CKPT_DIR, "pytorch_model.bin"), map_location="cpu"
)
ref_unet_params = torch.load(
    os.path.join(CKPT_DIR, "pytorch_model_1.bin"), map_location="cpu"
)

# 使用 strict=False 來跳過 shape 不匹配的層
unet.load_state_dict(unet_params, strict=False)
ref_unet.load_state_dict(ref_unet_params, strict=False)

# 移到裝置
text_encoder.to(DEVICE, dtype=torch.float32)
image_encoder.to(DEVICE, dtype=torch.float32)
vae.to(DEVICE, dtype=torch.float32)
ref_unet.to(DEVICE, dtype=torch.float32)
unet.to(DEVICE, dtype=torch.float32)

print("模型載入完成！")

# ============================
# 準備輸入
# ============================
print("\n處理輸入圖片...")


def process_image(image, totensor):
    if not image.mode == "RGBA":
        image = image.convert("RGBA")
    non_transparent = np.nonzero(np.array(image)[..., 3])
    if len(non_transparent[0]) > 0:
        min_x, max_x = non_transparent[1].min(), non_transparent[1].max()
        min_y, max_y = non_transparent[0].min(), non_transparent[0].max()
        image = image.crop((min_x, min_y, max_x, max_y))
    max_dim = max(image.width, image.height)
    max_height = max_dim
    max_width = int(max_dim / 3 * 2)
    new_image = Image.new("RGBA", (max_width, max_height))
    left = (max_width - image.width) // 2
    top = (max_height - image.height) // 2
    new_image.paste(image, (left, top))
    image = new_image.resize((512, 768))
    image = np.array(image).astype(np.float32) / 255.0
    if image.shape[-1] == 4:
        alpha = image[..., 3:4]
        bg_color = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        image = image[..., :3] * alpha + bg_color * (1 - alpha)
    return totensor(image)


totensor = transforms.ToTensor()
input_image = Image.open(INPUT_IMAGE).convert("RGBA")
imgs_in = process_image(input_image, totensor)
imgs_in = rearrange(imgs_in.unsqueeze(0).unsqueeze(0), "B Nv C H W -> (B Nv) C H W")

# 載入 pose
metas = json.load(open(POSE_JSON, "r"))
cameras = []
pose_images = []
input_path = os.path.join(CHARACTERGEN_2D, "material")
for lm in metas:
    cameras.append(
        torch.tensor(np.array(lm[0]).reshape(4, 4).transpose(1, 0)[:3, :4]).reshape(-1)
    )
    pose_images.append(
        totensor(
            np.asarray(
                Image.open(os.path.join(input_path, lm[1])).resize((768, 512))
            ).astype(np.float32)
            / 255.0
        )
    )

camera_matrixs = torch.stack(cameras).unsqueeze(0).to(DEVICE)
pose_imgs_in = torch.stack(pose_images).to(DEVICE)

print(f"Pose cameras: {camera_matrixs.shape}")
print(f"Pose images: {pose_imgs_in.shape}")

# ============================
# 建立 Pipeline
# ============================
print("\n建立推理 Pipeline...")
pipe = TuneAVideoPipeline(
    vae=vae,
    text_encoder=text_encoder,
    tokenizer=tokenizer,
    unet=unet,
    ref_unet=ref_unet,
    feature_extractor=feature_extractor,
    image_encoder=image_encoder,
    scheduler=noise_scheduler,
)
pipe.enable_vae_slicing()
pipe.enable_attention_slicing()
pipe.enable_sequential_cpu_offload()

# ============================
# 推理
# ============================
print("\n執行多視圖生成...")
generator = torch.Generator(device=DEVICE)
generator.manual_seed(2333)

prompts = "high quality, best quality"
prompt_ids = tokenizer(
    prompts,
    max_length=tokenizer.model_max_length,
    padding="max_length",
    truncation=True,
    return_tensors="pt",
).input_ids[0]

validation = {"video_length": 4}

with torch.autocast("cuda", dtype=torch.float32):
    imgs_in = imgs_in.to(DEVICE)
    out = pipe(
        prompt=prompts,
        image=imgs_in,
        generator=generator,
        num_inference_steps=40,
        camera_matrixs=camera_matrixs,
        prompt_ids=prompt_ids.to(DEVICE),
        height=768,
        width=512,
        unet_condition_type="image",
        pose_guider=None,
        pose_image=pose_imgs_in,
        use_noise=False,
        use_shifted_noise=False,
        **validation,
    ).videos
    out = rearrange(out, "B C f H W -> (B f) C H W", f=4)

# ============================
# 儲存結果
# ============================
print(f"\n生成 {out.shape[0]} 張多視圖圖片")
for i in range(out.shape[0]):
    output_path = Path(OUTPUT_DIR) / f"view_{i:02d}.png"
    save_image(out[i], output_path)
    print(f"  儲存: {output_path}")

# 合併為網格圖
grid = Image.new("RGB", (512 * 2, 768 * 2))
for i in range(min(4, out.shape[0])):
    img = Image.open(Path(OUTPUT_DIR) / f"view_{i:02d}.png")
    x = (i % 2) * 512
    y = (i // 2) * 768
    grid.paste(img, (x, y))

grid_path = Path(OUTPUT_DIR) / "multiview_grid.png"
grid.save(grid_path)
print(f"\n網格圖: {grid_path}")
print("\nCharacterGen 2D Stage 完成！")
