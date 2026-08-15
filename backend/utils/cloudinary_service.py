import cloudinary.uploader
from fastapi import UploadFile

async def upload_image(file:UploadFile, folder:str):
    contents = await file.read()

    result = cloudinary.uploader.upload(contents, folder=folder, resource_type="image")

    return result["secure_url"]