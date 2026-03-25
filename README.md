# s3_explorer.py
Gemini generated s3 bucket upload/download utility, using tkinter graphical interface. Requires local aws access keys stored at ~/.aws/credentials (or in the user home directory\\.aws\credentials on Windows). Also requires boto3 and at least Python 3.6. Depending on local color palette you may need to adjust color scheme via the dark mode button in the upper right hand corner of the ui. If running python3 that was installed by brew, you may need to install tkinter as well (brew install python-tk).
  
# s3_file_manager.py
CLI only tool to list an s3 bucket and upload and download files.  Uses boto3 and locally defined aws credentials.  Profiles can be specified via argument.

arguments:  
"bucket", "Name of the S3 bucket"  
"-p", "--profile", "AWS profile name - Default profile is [default]"  
"-d", "--download", "File key to download from S3"  
"-u", "--upload", "Local file path to upload to S3"  
"--prefix", "S3 folder/prefix for all operations", default=""
