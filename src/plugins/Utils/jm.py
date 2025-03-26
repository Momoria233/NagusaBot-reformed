import jmcomic
import os
import glob



option = jmcomic.create_option_by_file('option.yml')
jmcomic.download_album('1046534', option)

pdf_files = glob.glob(os.path.join(os.path.abspath(os.path.dirname(__file__)),'*.pdf'), recursive=False)

for pdf_file in pdf_files:
    new_name = os.path.join(os.path.dirname(pdf_file), 'pre01.pdf')
    os.rename(pdf_file, new_name)