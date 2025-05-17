# s3_explorer.py
Gemini generated s3 bucket upload/download utility, using tkinter graphical interface. Requires local aws access keys stored at ~/.aws/credentials (or in the user home directory\\.aws\credentials on Windows). Also requires boto3 and at least Python 3.6. Depending on local color palette some tweaks may be required (usually the text color and background color) in the class S3ClientGUI under:

  --- Color Customization ---
  bg_color = "#e5eb34"  # yellow  
  button_color = "#343aeb" # blue  
  text_color = "white"  
  background = "black"  
  
