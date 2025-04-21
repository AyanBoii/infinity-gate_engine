from diffusers import DiffusionPipeline, LCMScheduler
import torch
import os
import time
import sys
import traceback

# Set UTF-8 encoding for the entire script
sys.stdout.reconfigure(encoding='utf-8')

# Set device to use your RTX 4050
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

try:
    # Load base SDXL model
    model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    pipe = DiffusionPipeline.from_pretrained(
        model_id,
        variant="fp16",  # Load fp16 for VRAM savings
        torch_dtype=torch.float16
    )

    # Replace the scheduler with the LCM scheduler
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)

    # Load LoRA weights
    # First: LCM LoRA adapter (for fast inference)
    pipe.load_lora_weights("latent-consistency/lcm-lora-sdxl", adapter_name="lora")
    # Second: Pixel Art XL LoRA adapter
    pipe.load_lora_weights("nerijs/pixel-art-xl", adapter_name="pixel")

    # Set both adapters to use with specified weights
    pipe.set_adapters(["lora", "pixel"], adapter_weights=[1.0, 1.2])

    # Move pipeline to GPU
    pipe.to(device)

    # Prompt settings
    prompt = "pixel art style, A former elven archmage who left the Ivory Tower after a magical accident. Now seeks redemption through adventure. Eldara Moonweaver, traits: Intelligent, Mysterious, Haunted by past mistakes, Seeks knowledge, description: Tall and graceful with silver hair and glowing blue eyes. Wears flowing robes adorned with arcane symbols., in a Fantasy setting, world: A high-fantasy world with magic and mythical creatures. The realm is divided between the ancient elven forests, human kingdoms, and the mysterious Shadowlands."
    negative_prompt = "3d render, realistic, blurry, low quality, distorted, deformed"
    num_images = 1

    print(f"\n🎨 Generating image with prompt: {prompt}")
    print(f"📝 Negative prompt: {negative_prompt}")

    # Image generation
    image = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=8,
        guidance_scale=1.5,
    ).images[0]

    # Generate timestamp for unique filename
    timestamp = int(time.time())
    output_filename = f"pixel-art-xl-{timestamp}.png"

    # Get current working directory
    current_dir = os.getcwd()
    print(f"\n📁 Current working directory: {current_dir}")

    # Save the image with timestamp
    output_path = os.path.join(current_dir, output_filename)
    image.save(output_path)
    print(f"✅ Saved image to: {output_path}")

    # Copy the image to the frontend public directory
    frontend_dir = os.path.join(current_dir, "..", "infinity-gate_frontend", "public")
    frontend_path = os.path.join(frontend_dir, "pixel-art-xl-001.png")
    print(f"\n📁 Frontend directory: {frontend_dir}")

    try:
        image.save(frontend_path)
        print(f"✅ Copied image to frontend: {frontend_path}")
    except Exception as e:
        print(f"❌ Error copying to frontend: {str(e)}")
        print(f"❌ Error details: {str(e)}")

except Exception as e:
    print(f"❌ Error in image generation: {str(e)}")
    print(f"❌ Error details: {str(e)}")
    traceback.print_exc()
    sys.exit(1)