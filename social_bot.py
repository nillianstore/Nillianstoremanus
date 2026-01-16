import os
import json
import random
import requests
import frontmatter
from pathlib import Path

# Configuration
SHOP_DIR = Path("./shop")
LOG_FILE = Path("./social_log.json")
# IMPORTANT: Update this to your actual live domain once deployed
BASE_URL = "https://nillianstoremanus.netlify.app" 

# API Credentials (loaded from GitHub Secrets )
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
IG_USER_ID = os.getenv("IG_USER_ID")

def load_posted_history():
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_posted_history(product_id):
    history = load_posted_history()
    history.append(product_id)
    if len(history) > 50:
        history = history[-50:]
    with open(LOG_FILE, "w") as f:
        json.dump(history, f)

def get_random_product():
    products = list(SHOP_DIR.glob("*.md"))
    history = load_posted_history()
    available = [p for p in products if p.stem not in history]
    if not available:
        available = products
    return random.choice(available)

def parse_product(file_path):
    post = frontmatter.load(file_path)
    title = post.get("title", "Check out our latest product!")
    description = post.content.strip()[:500]
    price = post.get("price", "")
    amazon_link = post.get("link", "")
    
    image_path = post.get("cover", "")
    if not image_path and post.get("images"):
        image_path = post.get("images")[0]
    
    if image_path.startswith("./"):
        image_path = image_path[2:]
    elif image_path.startswith("/"):
        image_path = image_path[1:]
        
    image_url = f"{BASE_URL}/{image_path}"
    return {
        "id": file_path.stem,
        "title": title,
        "description": description,
        "price": price,
        "link": amazon_link,
        "image_url": image_url
    }

def generate_content(product_data):
    prompt = f"""
    You are a social media manager for 'Nillian Store', a boutique shop in the UAE.
    Product: {product_data['title']}
    Details: {product_data['description']}
    Price: {product_data['price']}
    Link: {product_data['link']}
    
    Create an engaging Instagram/Facebook post. 
    Include emojis, UAE context (Dubai/Abu Dhabi), and 10-15 hashtags.
    Format as JSON: {{"caption": "...", "hashtags": "..."}}
    """
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])

def post_to_instagram(image_url, caption):
    try:
        url = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media"
        r = requests.post(url, data={
            "image_url": image_url,
            "caption": caption,
            "access_token": META_ACCESS_TOKEN
        } )
        r.raise_for_status()
        creation_id = r.json()["id"]
        
        publish_url = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media_publish"
        r = requests.post(publish_url, data={
            "creation_id": creation_id,
            "access_token": META_ACCESS_TOKEN
        } )
        r.raise_for_status()
        return r.json().get("id")
    except Exception as e:
        print(f"IG Error: {e}")
        return None

def post_to_facebook(image_url, caption):
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        r = requests.post(url, data={
            "url": image_url,
            "message": caption,
            "access_token": META_ACCESS_TOKEN
        } )
        r.raise_for_status()
        return r.json().get("id")
    except Exception as e:
        print(f"FB Error: {e}")
        return None

def main():
    try:
        product_file = get_random_product()
        product_data = parse_product(product_file)
        ai_content = generate_content(product_data)
        full_caption = f"{ai_content['caption']}\n\n{ai_content['hashtags']}\n\nShop here: {product_data['link']}"
        
        ig_id = post_to_instagram(product_data["image_url"], full_caption)
        fb_id = post_to_facebook(product_data["image_url"], full_caption)
        
        if ig_id or fb_id:
            save_posted_history(product_data["id"])
            print(f"Success: Posted {product_data['id']}")
    except Exception as e:
        print(f"Automation Error: {e}")

if __name__ == "__main__":
    main()
