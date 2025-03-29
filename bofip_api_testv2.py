import requests
import json
import os
from transformers import pipeline
import streamlit as st

# === Étape 1 : Récupérer les données via l'API BOFIP ===
def fetch_all_bofip_data(api_url, filters):
    all_data = []
    offset = 0
    limit = 50
    while True:
        filters["offset"] = offset
        filters["limit"] = limit
        response = requests.get(api_url, params=filters)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if not results:
                break
            all_data.extend(results)
            offset += limit
        else:
            print(f"Erreur {response.status_code}: Impossible de récupérer les données.")
            break
    return {"results": all_data}

def save_data_locally(data, filename="bofip_data.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data_locally(filename="bofip_data.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# === Étape 2 : Préparer la base de connaissances ===
def prepare_knowledge_base(data):
    knowledge_base = []
    for record in data.get("results", []):
        fields = record.get("fields", {})
        title = fields.get("dc_title", "Titre inconnu")
        description = fields.get("dc_description", "Description indisponible")
        subject = fields.get("dc_subject", "Sujet inconnu")

        print(f"Titre: {title}, Sujet: {subject}")  # Débogage

        if any(keyword in subject for keyword in ["TVA", "Agriculture", "Impôts"]):
            content = f"Titre: {title}\nDescription: {description}\nSujet: {subject}"
            knowledge_base.append({"title": title, "content": content})

    if not knowledge_base:
        print("Aucune donnée pertinente trouvée dans les résultats de l'API.")
        return []

    return knowledge_base

# === Étape 3 : Utiliser un modèle de langage pour répondre aux questions ===
def answer_question(question, knowledge_base):
    if not question.strip():
        return "Veuillez poser une question valide."

    qa_pipeline = pipeline("question-answering")
    context = "\n".join([item["content"] for item in knowledge_base])

    if not context.strip():
        return "Aucune donnée disponible pour répondre à cette question."

    result = qa_pipeline(question=question, context=context)
    return result["answer"]

# === Étape 4 : Interface utilisateur avec Streamlit ===
def main():
    st.title("Assistant Fiscal Agricole")

    api_url = "https://www.data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/bofip-impots/records"
    filters = {
        "where": "dc_subject='TVA' OR dc_subject='Agriculture'",
        "select": "dc_title, dc_description, dc_subject",
        "limit": 50,
        "lang": "fr"
    }

    if not os.path.exists("bofip_data.json"):
        st.write("Chargement des données BOFIP via l'API...")
        data = fetch_all_bofip_data(api_url, filters)
        if data:
            save_data_locally(data)
        else:
            st.error("Impossible de charger les données BOFIP depuis l'API.")
    else:
        data = load_data_locally()

    knowledge_base = []
    if data:
        knowledge_base = prepare_knowledge_base(data)

    if not knowledge_base:
        st.error("Aucune donnée pertinente trouvée dans la base de connaissances.")
        st.warning("Vous pouvez toujours poser une question, mais la réponse risque d'être incomplète.")

    question = st.text_input("Posez votre question ici :", "")
    if question:
        with st.spinner("Recherche de la réponse..."):
            answer = answer_question(question, knowledge_base)
            if "Veuillez poser une question valide" in answer or "Aucune donnée disponible" in answer:
                st.warning(answer)
            else:
                st.success(f"Réponse : {answer}")

if __name__ == "__main__":
    main()