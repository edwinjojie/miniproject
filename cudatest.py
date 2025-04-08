import torch

def check_torch_and_cuda():
    print("Checking PyTorch and CUDA setup...\n")
    print(f"PyTorch version: {torch.__version__}")
    if torch.cuda.is_available():
        print("CUDA is available!")
        print(f"CUDA version: {torch.version.cuda}")
        print(f"Number of CUDA devices: {torch.cuda.device_count()}")
        print(f"Current device index: {torch.cuda.current_device()}")
        print(f"Current device name: {torch.cuda.get_device_name(torch.cuda.current_device())}")
        print(f"Is PyTorch built with CUDA support? {'Yes' if torch.backends.cuda.is_built() else 'No'}")
    else:
        print("CUDA is NOT available. Check your GPU drivers and CUDA installation.")

if __name__ == "__main__":
    check_torch_and_cuda()