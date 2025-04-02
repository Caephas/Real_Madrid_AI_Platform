import argparse
import os
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import classification_report, accuracy_score

class SimpleLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=1, output_dim=3):
        super(SimpleLSTM, self).__init__()
        # LSTM layer expects input of shape (batch, seq_length, input_dim)
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        # Fully connected layer maps the hidden state to output classes
        self.fc = nn.Linear(hidden_dim, output_dim)
    
    def forward(self, x):
        # x: shape (batch_size, seq_length, input_dim)
        lstm_out, (h_n, c_n) = self.lstm(x)
        # Use the hidden state from the last LSTM layer for classification
        out = self.fc(h_n[-1])
        return out

def train_model(train_loader, model, criterion, optimizer):
    model.train()
    for inputs, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(inputs)  # inputs should have shape (batch, seq_length, input_dim)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

def evaluate_model(test_loader, model):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for inputs, labels in test_loader:
            outputs = model(inputs)
            preds = torch.argmax(outputs, dim=1)
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.tolist())
    
    print("Accuracy:", accuracy_score(all_labels, all_preds))
    print(classification_report(all_labels, all_preds))

def create_sequences(data, targets, seq_length):
    """
    Convert the data into sequences using a sliding window approach.
    Each sequence is a window of `seq_length` consecutive rows,
    and the target is the label immediately following that window.
    """
    xs, ys = [], []
    for i in range(len(data) - seq_length):
        x_seq = data[i:i+seq_length]
        y_seq = targets[i+seq_length]
        xs.append(x_seq)
        ys.append(y_seq)
    return torch.tensor(xs, dtype=torch.float32), torch.tensor(ys, dtype=torch.long)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR"))
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN"))
    parser.add_argument("--test", type=str, default=os.environ.get("SM_CHANNEL_TEST"))
    parser.add_argument("--seq_length", type=int, default=5, help="Sequence length for LSTM input")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    args = parser.parse_args()

    FEATURES = [
        'venue_code', 'team', 'opp_code', 'hour', 'day_code',
        'gf_rolling', 'ga_rolling', 'sh_rolling', 'sot_rolling',
        'dist_rolling', 'fk_rolling', 'pk_rolling', 'pkatt_rolling',
        'opp_gf_rolling', 'opp_ga_rolling', 'opp_sh_rolling', 'opp_sot_rolling',
        'opp_dist_rolling', 'opp_fk_rolling', 'opp_pk_rolling', 'opp_pkatt_rolling'
    ]

    # Load data
    train_df = pd.read_csv(os.path.join(args.train, "train.csv"))
    test_df = pd.read_csv(os.path.join(args.test, "test.csv"))

    # Convert DataFrame to numpy arrays for features and target
    X_train_np = train_df[FEATURES].values
    y_train_np = train_df["target"].values
    X_test_np = test_df[FEATURES].values
    y_test_np = test_df["target"].values

    # Create sequences using a sliding window approach.
    # Each sequence has a length of args.seq_length and predicts the outcome of the following match.
    X_train_seq, y_train_seq = create_sequences(X_train_np, y_train_np, args.seq_length)
    X_test_seq, y_test_seq = create_sequences(X_test_np, y_test_np, args.seq_length)

    train_loader = DataLoader(TensorDataset(X_train_seq, y_train_seq), batch_size=32, shuffle=True)
    test_loader = DataLoader(TensorDataset(X_test_seq, y_test_seq), batch_size=32)

    # Define model, loss, and optimizer.
    # input_dim is the number of features per time step.
    input_dim = X_train_seq.shape[2]
    model = SimpleLSTM(input_dim=input_dim, hidden_dim=64, num_layers=1, output_dim=3)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Training loop
    for epoch in range(10):
        train_model(train_loader, model, criterion, optimizer)
        print(f"Epoch {epoch+1} done")

    # Evaluation
    evaluate_model(test_loader, model)

    # Save the trained model
    torch.save(model.state_dict(), os.path.join(args.model_dir, "lstm_model.pt"))