from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")

# Create NER pipeline
nlp = pipeline(  # type: ignore[call-overload]
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple",
)


def get_orgs(text, score_threshold=0.0):

    ner_results = nlp(text)
    orgs = list(set([ent['word'] for ent in ner_results if ent['entity_group']
                == 'ORG' and ent['score'] > score_threshold]))

    return orgs
