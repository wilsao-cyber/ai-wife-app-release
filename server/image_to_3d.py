import asyncio
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional
from config import ImageTo3DConfig
from PIL import Image
import io

logger = logging.getLogger(__name__)


class ImageTo3D:
    def __init__(self, config: ImageTo3DConfig):
        self.config = config
        self.provider = config.provider
        self.model_path = config.model_path
        self.output_format = config.output_format
        self.output_dir = Path("./output/models")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._triposr_dir = Path("./models/3d/TripoSR")

    async def initialize(self):
        logger.info(f"Initializing Image-to-3D with provider: {self.provider}")
        if self.provider == "triposr":
            await self._init_triposr()
        elif self.provider == "crm":
            await self._init_crm()
        else:
            raise ValueError(f"Unsupported Image-to-3D provider: {self.provider}")

    async def _init_triposr(self):
        if self._triposr_dir.exists():
            self._model = "triposr_cli"
            logger.info("TripoSR CLI ready")
        else:
            logger.warning("TripoSR not found, using mock converter")
            self._model = None

    async def _init_crm(self):
        try:
            from CRM import CRMModel

            self._model = CRMModel.from_pretrained(self.model_path)
            logger.info("CRM initialized")
        except ImportError:
            logger.warning("CRM not installed, using mock converter")
            self._model = None

    async def convert(self, image_data: bytes) -> str:
        session_id = uuid.uuid4().hex[:8]
        output_filename = f"character_{session_id}.{self.output_format}"
        output_path = self.output_dir / session_id
        output_path.mkdir(parents=True, exist_ok=True)

        if self._model == "triposr_cli":
            return await self._convert_triposr(image_data, output_path, output_filename)
        elif self._model and self.provider == "crm":
            return await self._convert_crm(image_data, output_path, output_filename)
        else:
            return await self._mock_convert(image_data, output_path, output_filename)

    async def _convert_triposr(
        self, image_data: bytes, output_path: Path, output_filename: str
    ) -> str:
        temp_image = output_path / "input.png"
        with open(temp_image, "wb") as f:
            f.write(image_data)

        try:
            process = await asyncio.create_subprocess_exec(
                "python",
                str(self._triposr_dir / "run.py"),
                str(temp_image),
                "--device",
                "cuda:0",
                "--chunk-size",
                "8192",
                "--mc-resolution",
                "256",
                "--output-dir",
                str(output_path),
                "--model-save-format",
                self.output_format,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                glb_path = output_path / f"mesh.{self.output_format}"
                if glb_path.exists():
                    final_path = output_path / output_filename
                    glb_path.rename(final_path)
                    logger.info(f"TripoSR generated: {output_filename}")
                    return output_filename

            logger.error(f"TripoSR failed: {stderr.decode()}")
            return await self._mock_convert(image_data, output_path, output_filename)

        except Exception as e:
            logger.error(f"TripoSR conversion failed: {e}")
            return await self._mock_convert(image_data, output_path, output_filename)

    async def _convert_crm(
        self, image_data: bytes, output_path: Path, output_filename: str
    ) -> str:
        image = Image.open(io.BytesIO(image_data))
        mesh = self._model.inference(image)
        final_path = output_path / output_filename
        mesh.save(str(final_path))
        return output_filename

    async def _mock_convert(
        self, image_data: bytes, output_path: Path, output_filename: str
    ) -> str:
        final_path = output_path / output_filename
        with open(final_path, "wb") as f:
            f.write(b"mock_3d_model")
        logger.warning(f"Using mock 3D model output: {output_filename}")
        return output_filename

    async def convert_from_file(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            image_data = f.read()
        return await self.convert(image_data)
