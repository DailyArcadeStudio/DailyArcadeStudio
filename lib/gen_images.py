"""TFgamestudio: SDXLで物語シーンの絵を生成。
problem.json の kind=="image" シーンの prompt から <out>/imgs/<idx>.png を作る。
usage: python gen_images.py <problem.json> <out_dir>
16:9 (1344x768) で生成。MPS/16GB対策で attention slicing。
"""
import sys, json
from pathlib import Path
import torch
from diffusers import StableDiffusionXLPipeline

NEG = "text, watermark, signature, letters, words, deformed, blurry, low quality, extra limbs, distorted faces"

def main(prob_path, out_dir):
    prob = json.loads(Path(prob_path).read_text())
    out = Path(out_dir); (out/"imgs").mkdir(parents=True, exist_ok=True)
    img_scenes = [(i,s) for i,s in enumerate(prob["scenes"]) if s.get("kind")=="image"]
    if not img_scenes:
        print("NO_IMAGE_SCENES"); return
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("mps")
    pipe.enable_attention_slicing()
    for idx, s in img_scenes:
        dst = out/"imgs"/f"{idx:02d}.png"
        if dst.exists():
            print(f"SKIP {dst.name}", flush=True); continue
        image = pipe(prompt=s["prompt"], negative_prompt=NEG,
                     width=1344, height=768, num_inference_steps=28,
                     guidance_scale=7.0,
                     generator=torch.Generator("cpu").manual_seed(1200+idx)).images[0]
        image.save(dst)
        print(f"IMG_OK {dst.name}", flush=True)
    print("ALL_IMG_DONE", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
