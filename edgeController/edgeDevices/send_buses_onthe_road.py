import os
import subprocess, time

def run_busai(script_path, arguments):
    command = ['python', script_path] + arguments

    try:
        subprocess.Popen(command)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Example usage:
current_folder = os.path.dirname(os.path.realpath(__file__))
busai_script = os.path.join(current_folder, "busai.py")
ids = []
i=1

while i <4:
    ids.append(['urn:ngsild:CrowdFlowObserved:Bus:'+str(i), 'urn:ngsild:Vehicle:Bus:'+str(i)])
    run_busai(busai_script, ids[-1])
    i+=1
    time.sleep(300)



