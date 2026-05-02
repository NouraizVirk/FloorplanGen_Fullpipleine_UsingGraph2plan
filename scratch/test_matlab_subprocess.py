import subprocess
import os
import scipy.io as sio
import numpy as np

def test_matlab():
    matlab_exe = r'E:\MySoftwares\Softwares\MATLAB\R2026a\bin\matlab.exe'
    
    # Create dummy data
    boundary = np.array([[0,0,0,0], [100,0,1,0], [100,100,2,0], [0,100,3,0]])
    box = np.array([[20,20,80,80,0]])
    rType = np.array([0])
    edge = np.array([[0,0,0]])
    
    input_file = os.path.abspath('input.mat')
    output_file = os.path.abspath('output.mat')
    
    sio.savemat(input_file, {
        'boundary': boundary,
        'box': box,
        'rType': rType,
        'edge': edge
    })
    
    # MATLAB command
    # We need to add the path to align_fp directory
    align_fp_dir = os.path.abspath(r'E:\Projects\FYP\Graph2Plan\Graph2plan\Interface\align_fp')
    
    ml_cmd = (
        f"addpath('{align_fp_dir}'); "
        f"load('{input_file}'); "
        f"[box_out, box_order, rBoundary] = align_fp(boundary, box, rType, edge, 18, false); "
        f"save('{output_file}', 'box_out', 'box_order', 'rBoundary');"
    )
    
    full_cmd = [matlab_exe, "-batch", ml_cmd]
    print(f"Running: {' '.join(full_cmd)}")
    
    try:
        subprocess.run(full_cmd, check=True, capture_output=True, text=True)
        if os.path.exists(output_file):
            res = sio.loadmat(output_file)
            print("SUCCESS! Result keys:", res.keys())
            print("box_out shape:", res['box_out'].shape)
        else:
            print("ERROR: Output file not created")
    except Exception as e:
        print(f"ERROR: {e}")
        if hasattr(e, 'stderr'):
            print(f"Stderr: {e.stderr}")

if __name__ == '__main__':
    test_matlab()
