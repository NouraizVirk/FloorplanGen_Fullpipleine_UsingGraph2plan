import subprocess
import os
import scipy.io as sio
import numpy as np
import uuid

class MatlabProxy:
    def __init__(self, matlab_exe=r'E:\MySoftwares\Softwares\MATLAB\R2026a\bin\matlab.exe'):
        self.matlab_exe = matlab_exe
        self.paths = []

    def addpath(self, path):
        self.paths.append(path)

    def genpath(self, path):
        return f"genpath('{os.path.abspath(path)}')"

    def align_fp(self, boundary, box, rType, edge, threshold, flag, nargout=3):
        temp_id = str(uuid.uuid4())[:8]
        input_file = os.path.abspath(f'temp_in_{temp_id}.mat')
        output_file = os.path.abspath(f'temp_out_{temp_id}.mat')
        
        try:
            sio.savemat(input_file, {
                'boundary': np.array(boundary).astype(np.float64),
                'box': np.array(box).astype(np.float64),
                'rType': np.array(rType).astype(np.float64),
                'edge': np.array(edge).astype(np.float64),
                'threshold': float(threshold),
                'flag': bool(flag)
            })
            
            path_cmds = "".join([f"addpath({p}); " if p.startswith("genpath") else f"addpath('{os.path.abspath(p)}'); " for p in self.paths])
            ml_cmd = (
                f"{path_cmds} "
                f"load('{input_file}'); "
                f"[box_out, box_order, rBoundary] = align_fp(boundary, box, rType, edge, threshold, flag); "
                f"save('{output_file}', 'box_out', 'box_order', 'rBoundary');"
            )
            
            print(f"Running MATLAB...")
            subprocess.run([self.matlab_exe, "-batch", ml_cmd], check=True, capture_output=True, text=True)
            
            if os.path.exists(output_file):
                res = sio.loadmat(output_file)
                os.remove(input_file)
                os.remove(output_file)
                return [res['box_out'], res['box_order'], res['rBoundary']]
            else:
                raise RuntimeError("MATLAB failed to produce output file.")
        except Exception as e:
            if os.path.exists(input_file): os.remove(input_file)
            if os.path.exists(output_file): os.remove(output_file)
            print(f"MatlabProxy Error: {e}")
            if hasattr(e, 'stderr'): print(f"Stderr: {e.stderr}")
            raise

def test():
    proxy = MatlabProxy()
    proxy.addpath(r'E:\Projects\FYP\Graph2Plan\Graph2plan\Interface\align_fp')
    
    # Real-ish data from the screenshot
    boundary = np.array([
        [0, 0, 0, 0],
        [256, 0, 1, 0],
        [256, 256, 2, 0],
        [0, 256, 3, 0]
    ])
    box = np.array([
        [10, 10, 50, 50, 1],
        [60, 60, 100, 100, 2]
    ])
    rType = np.array([1, 2])
    edge = np.array([[0, 1, 0]])
    
    try:
        res = proxy.align_fp(boundary, box, rType, edge, 18, False)
        print("SUCCESS")
        rBoundary = res[2]
        print("rBoundary type:", type(rBoundary))
        print("rBoundary shape:", rBoundary.shape)
        if isinstance(rBoundary, np.ndarray):
            rb_flat = rBoundary.flatten()
            print("Flattened length:", len(rb_flat))
            for i, rb in enumerate(rb_flat):
                print(f"rb[{i}] shape:", rb.shape)
                print(f"rb[{i}] data:", rb)
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == '__main__':
    test()
