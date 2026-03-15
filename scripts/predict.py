import torch
import numpy as np
from train_model import FitnessNet, scaler, class_map

sample_student = np.array([[165, 50, 18.4, 3200, 7.9, 175]])
sample_scaled = torch.tensor(scaler.transform(sample_student), dtype=torch.float32)

model = FitnessNet()
model.load_state_dict(torch.load("../models/fitness_model.pth"))
model.eval()

with torch.no_grad():
    pred_class = torch.argmax(model(sample_scaled), dim=1).item()
    print(f"预测体质等级：{class_map[pred_class]}")
