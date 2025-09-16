import torch
from diffusers import StableDiffusionPipeline
import streamlit as st

# Load model
@st.cache_resource
def load_model():
    model_id = "runwayml/stable-diffusion-v1-5"
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return pipe.to(device)

st.set_page_config(page_title="Concept to Picture App", page_icon="🎨")

st.title("🎨 Concept to Picture App (No API Key)")
st.write("Enter any idea and this app will create a picture for you!")

concept = st.text_input("Enter your concept:")

if st.button("Generate Image"):
    if concept.strip() == "":
        st.warning("Please type something first!")
    else:
        st.write("⏳ Generating your image... This may take a while the first time.")
        pipe = load_model()
        with torch.autocast("cuda" if torch.cuda.is_available() else "cpu"):
            image = pipe(concept).images[0]

        # Show image
        st.image(image, caption="Generated Image", use_container_width=True)

        # Save + download option
        image.save("generated_image.png")
        with open("generated_image.png", "rb") as file:
            st.download_button(
                label="Download Image",
                data=file,
                file_name="generated_image.png",
                mime="image/png")
