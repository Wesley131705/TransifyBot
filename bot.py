import discord
from discord.ext import commands, tasks
import random
import re
import os
import asyncio
from fpdf import FPDF
import requests
from flask import Flask
from threading import Thread

# --- Configuration des intents Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

frais_livraison = random.randint(70, 350)

# --- Téléchargement du logo s'il n'existe pas
def download_logo():
    if not os.path.exists("logo.png"):
        url = "https://i.ibb.co/s9NQHrDQ/Logo-Transify-removebg-preview.png"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open("logo.png", "wb") as f:
                    f.write(response.content)
                print("✅ Logo téléchargé avec succès")
            else:
                print(f"⚠️ Échec téléchargement logo, status code: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Erreur téléchargement logo : {e}")

download_logo()

# --- Quand le bot est prêt
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    update_frais_livraison.start()

# --- Tâche pour mettre à jour les frais de livraison
@tasks.loop(minutes=1)
async def update_frais_livraison():
    global frais_livraison
    frais_livraison = random.randint(70, 350)
    print(f"💸 Nouveau frais de livraison : {frais_livraison} EUR")

# --- Gestion du numéro de bon de livraison
def get_next_delivery_number():
    try:
        with open("compteur.txt", "r+") as f:
            last = int(f.read())
            new = last + 1
            f.seek(0)
            f.write(str(new))
            f.truncate()
            return f"BL-{new:05d}"
    except FileNotFoundError:
        with open("compteur.txt", "w") as f:
            f.write("1")
        return "BL-00001"

# --- Extraction des infos de la facture
def extract_facture_infos(content):
    nom = re.search(r"Nom du client:\s*(.+)", content)
    entreprise = re.search(r"Entreprise:\s*(.+)", content)
    telephone = re.search(r"Téléphone:\s*(.+)", content)
    return (
        nom.group(1).strip() if nom else "Non spécifié",
        entreprise.group(1).strip() if entreprise else "Non spécifié",
        telephone.group(1).strip() if telephone else "Non spécifié"
    )

# --- Génération du PDF
def generate_bon_livraison_pdf(nom, entreprise, telephone, frais_livraison_valeur, numero):
    pdf = FPDF()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()

    try:
        pdf.image("logo.png", x=15, y=10, w=40)
    except Exception as e:
        print(f"⚠️ Erreur logo : {e}")

    pdf.set_y(45)
    pdf.set_fill_color(0, 191, 254)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "Bon de Livraison", ln=True, align="C", fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Numéro : {numero}", ln=True)
    pdf.cell(0, 10, f"Nom du client : {nom}", ln=True)
    pdf.cell(0, 10, f"Entreprise : {entreprise}", ln=True)
    pdf.cell(0, 10, f"Téléphone : {telephone}", ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Frais de livraison (compté en plus de la facture) : {frais_livraison_valeur} EUR")
    pdf.ln(10)
    pdf.cell(0, 10, "Entreprise (Fournisseur) : Transify", ln=True)
    pdf.cell(0, 10, "PDG : Wesley Stone", ln=True)

    filename = f"bon_livraison_{numero}.pdf"
    pdf.output(filename)
    return filename

# --- Gestion des messages
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.category and "🛒 passer commande" in message.channel.category.name.lower():
        if re.match(r"=+ FACTURE ===", message.content.strip(), re.IGNORECASE):
            frais = frais_livraison
            numero = get_next_delivery_number()
            nom, entreprise, telephone = extract_facture_infos(message.content)

            await message.channel.send(
                f"Bonjour 👋\n"
                f"Les frais de livraison pour cette demande s’élèvent à **{frais} EUR**.\n"
                f"⚠️ **Ce montant n’est pas mentionné dans la facture ci-dessus, il est ajouté automatiquement.**\n\n"
                "Merci de votre compréhension. N’hésitez pas à nous écrire si vous avez la moindre question.\n\n"
                "-- L’équipe Transify"
            )

            try:
                pdf_path = generate_bon_livraison_pdf(nom, entreprise, telephone, frais, numero)
                await asyncio.sleep(0.5)
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        file = discord.File(f, filename=pdf_path)
                        await message.channel.send("📎 Voici le bon de livraison :", file=file)
            except Exception as e:
                print(f"❌ Erreur PDF : {e}")
            finally:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

    await bot.process_commands(message)

# --- Serveur Flask keep_alive (Replit / Render)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Lancer le serveur Flask et le bot Discord
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
