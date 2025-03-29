iimport requests
import json
import os
from transformers import pipeline
import streamlit as st

# === Étape 1 : Récupérer les données via l'API BOFIP ===
def fetch_bofip_data(api_url, filters):
    """
    Récupère les données BOFIP via l'API avec des filtres spécifiques.
    """
    try:
        response = requests.get(api_url, params=filters)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erreur {response.status_code}: Impossible de récupérer les données.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Erreur de connexion : {e}")
        return None

def save_data_locally(data, filename="bofip_data.json"):
    """
    Sauvegarde les données BOFIP localement dans un fichier JSON.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data_locally(filename="bofip_data.json"):
    """
    Charge les données BOFIP depuis un fichier JSON local.
    """
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# === Étape 2 : Préparer la base de connaissances ===
def prepare_knowledge_base(data):
    """
    Transforme les données BOFIP en une base de connaissances structurée.
    """
    knowledge_base = []
    for record in data.get("results", []):
        fields = record.get("fields", {})
        title = fields.get("dc_title", "Titre inconnu")
        description = fields.get("dc_description", "Description indisponible")
        subject = fields.get("dc_subject", "Sujet inconnu")

        # Ajouter uniquement les données pertinentes
        if any(keyword in subject for keyword in ["TVA", "Agriculture", "Impôts"]):
            content = f"Titre: {title}\nDescription: {description}\nSujet: {subject}"
            knowledge_base.append({"title": title, "content": content})
    return knowledge_base

# === Étape 3 : Utiliser un modèle de langage pour répondre aux questions ===
def answer_question(question, knowledge_base):
    """
    Utilise un modèle de question-réponse pour interroger la base de connaissances.
    """
    qa_pipeline = pipeline("question-answering")
    
    # Concaténer tous les contenus pour former le contexte global
    context = "\n".join([item["content"] for item in knowledge_base])
    
    # Obtenir la réponse
    result = qa_pipeline(question=question, context=context)
    return result["answer"]

# === Étape 4 : Interface utilisateur avec Streamlit ===
def main():
    st.title("Assistant Fiscal Agricole")

    # URL de l'API BOFIP
    api_url = "https://www.data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/bofip-impots/records"

    # Définir les filtres pour cibler les données pertinentes
    filters = {
        "where": "dc_subject='TVA' OR dc_subject='Agriculture'",  # Filtrer par sujet pertinent
        "select": "dc_title, dc_description, dc_subject",          # Sélectionner les champs pertinents
        "limit": 50,                                               # Limiter le nombre de résultats
        "lang": "fr"                                               # Spécifier la langue
    }

    # Charger les données BOFIP (locale ou API)
    if not os.path.exists("bofip_data.json"):
        st.write("Chargement des données BOFIP via l'API...")
        data = fetch_bofip_data(api_url, filters)
        if data:
            save_data_locally(data)
    else:
        data = load_data_locally()

    if data:
        knowledge_base = prepare_knowledge_base(data)
        
        # Interface utilisateur
        question = st.text_input("Posez votre question ici :", "")
        if question:
            with st.spinner("Recherche de la réponse..."):
                answer = answer_question(question, knowledge_base)
                st.success(f"Réponse : {answer}")
    else:
        st.error("Impossible de charger les données BOFIP.")

if __name__ == "__main__":
    main()