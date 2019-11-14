import pandas as pd
from sqlalchemy import create_engine
import re
import os
from datetime import datetime, timedelta
pd.set_option('expand_frame_repr', False)
option_eg = create_engine('')
stk_eg = create_engine('')

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, os.pardir))
DATA_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir, 'data'))

if not os.path.exists(DATA_ROOT):
    os.makedirs(DATA_ROOT)


def _get_abs_path_from_root(root, *args, auto_folder, as_folder):
    abs_path = os.path.abspath(os.path.join(root, *args))
    if as_folder:
        folder_path = abs_path
    else:
        folder_path = os.path.abspath(os.path.join(abs_path, os.pardir))

    if auto_folder and not os.path.exists(folder_path):
        os.makedirs(folder_path)

    return abs_path


def get_abs_path_from_data(*args, auto_folder=True, as_folder=False):
    return _get_abs_path_from_root(DATA_ROOT, *args, auto_folder=auto_folder, as_folder=as_folder)
