from typing import Union
from fastapi import HTTPException
import httpx
import base64
import json
import io

# 1. Definisikan URL dan Kunci API
GEMINI_API_KEY = "AIzaSyBWwyo_IDUCZhh-j6kEslyrtze6G9m5svI"  # Ganti dengan kunci API Anda yang sebenarnya
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?key={GEMINI_API_KEY}"

IMAGE_URL_1 = 'https://opzvlvujgtbntrrtnwiz.supabase.co/storage/v1/object/public/pics/Ferdiansyah2025-09-27%2009:07:27.jpg'
IMAGE_URL_2 = 'https://opzvlvujgtbntrrtnwiz.supabase.co/storage/v1/object/public/pics/Septyan%20Rikaldi%20Pratama%20S.Ikom2025-09-30%2010:33:02.jpg'

def get_base64_from_url(url: str) -> str:
    try:
        # Menggunakan httpx.get() untuk mengambil data biner
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status() # Cek jika ada error HTTP
        # Mengonversi data biner menjadi string Base64
        return base64.b64encode(response.content).decode('utf-8')
    except httpx.HTTPError as e:
        print(f"Error saat mengambil gambar dari {url}: {e}")
        return ""

# 2. Ambil dan konversi kedua gambar


def compare_image(img1:str, img2:str) -> Union[str,bool]:
    all_response_text = ""

    base64_image1 = get_base64_from_url(img1)
    base64_image2 = get_base64_from_url(img2)

    # Cek jika konversi gagal
    if not base64_image1 or not base64_image2:
        exit()

    # 3. Definisikan Payload JSON (Body Request)
    payload = {
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                    },
                    "status": {
                        "type": "boolean"
                    }
                }
            }
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Apakah 2 orang in sama, contoh respon adalah {status:menggambarkan apakah gambar ini merupakan 2 orang yang sama, dan terdapat foto orang yang menjadi object utama, serta pastikan foto ini tidak terlalu gelap, terang ataupun blur,message:output berupa penjelasan singkat tentang 2 foto itu}"
                    },
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_image1
                        }
                    },
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_image2
                        }
                    }
                ]
            }
        ]
    }
    try:
        with httpx.stream("POST", API_URL, json=payload, timeout=30) as response:
            response.raise_for_status()
            
            for chunk in response.iter_lines():
                all_response_text += chunk
            

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        return False
    except httpx.RequestError as e:
        print(f"An error occurred while requesting: {e}")
        return False

    response = ""    
    for data in eval(all_response_text):
        response += str.replace(str.replace(data['candidates'][0]['content']['parts'][0]['text'], 'false', 'False'),'true','True')

    return eval(response)