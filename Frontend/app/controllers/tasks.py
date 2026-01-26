import os
import time
import shutil

def clean_user_files(obj_dir):
    """
    Erases the files inside 'obj_dir' older than 24 hours

    Args:
        obj_dir: absolute path to the folder whose contents we want to delete
    """
    if not obj_dir or not os.path.exists(obj_dir):
        print(f"The folder {obj_dir} doesn't exist or is not configurated.")
        return

    now = time.time()
    limite_segundos = 10  # 24 hours

    # Iterate through all the items inside obj_dir
    for item in os.listdir(obj_dir):
        abs_path = os.path.join(obj_dir, item)
        
        try:
            # 1. Get the modification time 
            t_mod = os.path.getmtime(abs_path)
            is_old = (now - t_mod) > limite_segundos

            if is_old:
                # CASE A: a folder
                if os.path.isdir(abs_path):
                    shutil.rmtree(abs_path)
                    print(f"Deleted folder: {item}")
                # CASE B: a file
                elif os.path.isfile(abs_path):
                    os.remove(abs_path)
                    print(f"Deleted file: {item}")

        except Exception as e:
            print(f"Exception while trying to delete {item}: {e}")