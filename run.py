import os
import subprocess
import sys

def main():
    print("==================================================")
    print("    Concrete Compressive Strength Predictor       ")
    print("        AI-Driven Civil Engineering App          ")
    print("==================================================")
    
    # Get current working directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    
    # 1. Check if model and metrics exist
    model_path = os.path.join(backend_dir, "model.joblib")
    metrics_path = os.path.join(backend_dir, "metrics.json")
    
    if not os.path.exists(model_path) or not os.path.exists(metrics_path):
        print("\n[INFO] ML model or metrics not found. Starting model training pipeline...")
        train_script = os.path.join(backend_dir, "train.py")
        
        try:
            # Run the training script
            subprocess.run([sys.executable, train_script], check=True)
            print("[SUCCESS] ML model trained and evaluated successfully.\n")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to run training script: {e}")
            sys.exit(1)
    else:
        print("\n[INFO] Pre-trained ML model and metrics found. Ready to serve.")
        
    # 2. Start FastAPI Server using uvicorn
    print("[INFO] Starting FastAPI Web Server...")
    print("[INFO] Application will be available at: http://localhost:8000\n")
    
    try:
        # Run uvicorn server
        # We run it as a subprocess to let uvicorn print to stdout directly
        subprocess.run([
            sys.executable, "-m", "uvicorn", "backend.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], check=True)
    except KeyboardInterrupt:
        print("\n[INFO] Web server stopped by user.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Web server crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
