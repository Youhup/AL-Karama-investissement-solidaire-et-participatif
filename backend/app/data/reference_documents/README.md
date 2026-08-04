# Documents de référence (RAG du chat)

Déposez ici les documents de référence à rendre consultables par le chat :
extraits de loi (ex. cadre légal de l'ESS au Maroc), définitions
officielles, glossaires... Ce contenu est public et visible par tous les
rôles (visiteur, porteur, investisseur, admin).

**Ne mettez jamais ici** de document contenant des données personnelles ou
confidentielles (ce dossier est indexé globalement, sans contrôle d'accès).

## Formats acceptés
`.txt`, `.md`, `.pdf`, `.jpg`, `.jpeg`, `.png` — le texte des PDF/images est
extrait via le même moteur OCR que les documents projet
(`app/services/ocr_service.py`).

## Utilisation

1. Copiez votre fichier ici, par exemple `loi-47-15-ess.pdf`.
2. Réindexez la base de connaissances (depuis `backend/`) :

   ```
   python index_knowledge_base.py
   ```

   (ou `docker compose exec api python index_knowledge_base.py` si vous
   utilisez Docker.)

Le fichier est découpé en fragments, vectorisé, puis indexé sous
`source_type=reference`. Une réindexation remplace entièrement les
fragments précédents pour ce fichier — vous pouvez éditer/remplacer un
fichier et relancer la commande sans dupliquer le contenu.
