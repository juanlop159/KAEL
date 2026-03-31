import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")
tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1", dtype=torch.float16, device_map="auto")
lora_config = LoraConfig(task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16, lora_dropout=0.1)
model = get_peft_model(model, lora_config)

data = [json.loads(l) for l in open("/workspace/kael_training.jsonl")]
texts = ["Usuario: "+d["messages"][0]["content"]+"\nKAEL: "+d["messages"][1]["content"] for d in data]
dataset = Dataset.from_dict({"text": texts})

def tok(x):
    return tokenizer(x["text"], truncation=True, max_length=128, padding="max_length")

dataset = dataset.map(tok)
dataset = dataset.map(lambda x: {"labels": x["input_ids"]})

args = TrainingArguments(output_dir="/workspace/kael_ft", num_train_epochs=3, per_device_train_batch_size=1, fp16=True)
trainer = Trainer(model=model, args=args, train_dataset=dataset, data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False))
trainer.train()
model.save_pretrained("/workspace/kael_ft")
print("COMPLETADO")
