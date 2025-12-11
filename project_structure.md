# Project Structure

```
.
├── .gitignore
├── DO_NOT_UPLOAD_steady-dryad-478107-j9-cee216d247f2.json
├── SCRAPER_USAGE.md
├── app_01.py
├── download_log.txt
├── for me.txt
├── instructions.md
├── requirements.txt
├── tags.xlsx
├── app/
│   ├── __init__.py
│   ├── app.py
│   ├── constants.py
│   ├── data_loader.py
│   ├── filters.py
│   ├── ui_components.py
│   └── utils.py
├── data/
│   ├── analysis/
│   ├── merged/
│   ├── processed/
│   └── raw/
└── scripts/
    ├── query_database.py
    ├── data_analysis/
    │   ├── tag_processor_batch.py
    │   └── tag_processor_test.py
    ├── data_processing/
    │   ├── analyze_full_text_lengths.py
    │   ├── create_full_text_for_llm.py
    │   ├── merge_scholarships_attachments.py
    │   └── merge_tags_with_metadata.py
    └── get_data/
        ├── cloud_ocr_processor.py
        ├── document_parsing_and_OCR_staging.py
        ├── download_attachments.py
        ├── scrape_scholarships.py
        └── utils/
            ├── convert_csv_to_json.py
            ├── doc_to_pdf.py
            ├── image_to_pdf.py
            └── verify_attachments_downloads.py
```
