import math
import os
import re
import json
import datetime
from pathlib import Path

import torch
import numpy as np
import rasterio
from einops import repeat
from torch import nn
from torchvision.transforms import v2

# Import necessary components from the officially downloaded Clay model
from claymodel.model import Encoder
from claymodel.utils import posemb_sincos_2d_with_gsd

class EmbeddingEncoder(Encoder):
    """Clay Encoder without mask and shuffle, adapted from factory."""
    def __init__(self, img_size, patch_size, dim, depth, heads, dim_head, mlp_ratio):
        super().__init__(
            mask_ratio=0.0,
            shuffle=False,
            patch_size=patch_size,
            dim=dim,
            depth=depth,
            heads=heads,
            dim_head=dim_head,
            mlp_ratio=mlp_ratio,
        )
        self.img_size = img_size
        self.grid_size = img_size // patch_size
        self.num_patches = self.grid_size**2

    def add_encodings(self, patches, time, latlon, gsd):
        B, L, D = patches.shape
        grid_size = self.grid_size
        pos_encoding = posemb_sincos_2d_with_gsd(
            h=grid_size, w=grid_size, dim=(self.dim - 8), gsd=gsd
        ).to(patches.device).detach()

        time_latlon = torch.hstack((time, latlon)).to(patches.device).detach()
        pos_encoding = repeat(pos_encoding, "L D -> B L D", B=B)
        time_latlon = repeat(time_latlon, "B D -> B L D", L=L)
        pos_metadata_encoding = torch.cat((pos_encoding, time_latlon), dim=-1)
        return patches + pos_metadata_encoding

    def forward(self, datacube):
        cube, time, latlon, gsd, waves = (
            datacube["pixels"], datacube["time"], datacube["latlon"],
            datacube["gsd"], datacube["waves"]
        )
        B, C, H, W = cube.shape

        patches, _ = self.to_patch_embed(cube, waves)
        patches = self.add_encodings(patches, time, latlon, gsd)

        cls_tokens = repeat(self.cls_token, "1 1 D -> B 1 D", B=B)
        patches = torch.cat((cls_tokens, patches), dim=1)

        patches = self.transformer(patches)
        embeddings = patches[:, 0, :]
        return embeddings

class Embedder(nn.Module):
    def __init__(self, ckpt_path, img_size=256, device="cpu"):
        super().__init__()
        self.device = torch.device(device)
        self.img_size = img_size
        
        self.clay_encoder = EmbeddingEncoder(
            img_size=img_size, patch_size=8, dim=1024,
            depth=24, heads=16, dim_head=64, mlp_ratio=4.0
        ).to(self.device)

        self.load_clay_weights(ckpt_path)

    def load_clay_weights(self, ckpt_path):
        print(f"Loading checkpoint from {ckpt_path}...")
        ckpt = torch.load(ckpt_path, map_location=self.device, mmap=True, weights_only=False)
        state_dict = ckpt.get("state_dict", ckpt)
        
        # Try both 'model.encoder' and 'model.teacher' patterns
        encoder_pattern = re.compile(r"^model\.(encoder|teacher)\.")
        state_dict = {
            encoder_pattern.sub("", name): param
            for name, param in state_dict.items()
            if encoder_pattern.match(name)
        }

        print(f"Filtering state_dict: {len(state_dict)} parameters")

        loaded_count = 0
        with torch.no_grad():
            for name, param in self.clay_encoder.named_parameters():
                if name in state_dict and param.size() == state_dict[name].size():
                    param.data.copy_(state_dict[name])
                    loaded_count += 1
                elif name in state_dict:
                    print(f"Warning: Size mismatch for {name}: expected {param.size()}, got {state_dict[name].size()}")
                else:
                    print(f"Warning: {name} not found in checkpoint")

        print(f"Loaded {loaded_count}/{len(list(self.clay_encoder.named_parameters()))} parameters")

        for param in self.clay_encoder.parameters():
            param.requires_grad = False
        self.clay_encoder.eval()
        print("Clay model loaded and set to evaluation mode")

    def forward(self, datacube):
        return self.clay_encoder(datacube)
