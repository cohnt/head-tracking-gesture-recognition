import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import torch
from torch.autograd import Variable
import face_dataset
from sklearn.model_selection import train_test_split
import torch.optim as optim
from tqdm import tqdm
import matplotlib.pyplot as plt

class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.CONV1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3)
        self.CONV2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3)
        self.CONV3 = nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3)
        self.CONV4 = nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3)
        self.CONV5 = nn.Conv2d(in_channels=128, out_channels=128, kernel_size=3)
        self.CONV6 = nn.Conv2d(in_channels=128, out_channels=256, kernel_size=3)
        self.FC1=nn.Linear(6400,1024)
        self.FC2=nn.Linear(1024,136)
        self.POOL = nn.MaxPool2d(2,2)
        self.DROP = nn.Dropout(p=0.2)

    def forward(self, h):
        # print(h.detach().numpy().shape)
        h = self.CONV1(h)
        h = F.relu(h)
        h = self.POOL(h)
        h = self.DROP(h)

        h = self.CONV2(h)
        h = F.relu(h)
        h = self.POOL(h)
        h = self.DROP(h)

        h = self.CONV3(h)
        h = F.relu(h)
        h = self.POOL(h)
        h = self.DROP(h)

        h = self.CONV4(h)
        h = F.relu(h)
        h = self.POOL(h)
        h = self.DROP(h)

        h = self.CONV5(h)
        h = F.relu(h)
        h = self.POOL(h)
        h = self.DROP(h)

        h = self.CONV6(h)
        h = F.relu(h)
        h = self.POOL(h)
        h = self.DROP(h)
        # print(h.detach().numpy().shape)

        h = h.view(h.size(0), -1)

        h = self.FC1(h)
        h = F.relu(h)
        h = self.DROP(h)
        h = self.FC2(h)

        return h

def train(epoch, train_dataset, valid_dataset, train_losses, val_losses, use_loading_bar=True, use_cuda=True):
    model.train()

    cur_train_loss = 0.0
    cur_valid_loss = 0.0

    for x_train, y_train in (tqdm(train_dataset) if use_loading_bar else train_dataset):
        # getting the training set
        x_train, y_train = Variable(torch.tensor(x_train).unsqueeze(1).float()), Variable(torch.tensor(y_train.reshape(y_train.shape[0],-1)).float())
        if torch.cuda.is_available() and use_cuda:
            x_train = x_train.cuda()
            y_train = y_train.cuda()
        optimizer.zero_grad()
        output = model(x_train)
        loss = criterion(output, y_train)
        loss.backward()
        optimizer.step()
        cur_train_loss += loss.item() * x_train.size(0)

    x_sample = None
    y_sample = None
    y_out = None

    model.eval()
    for x_val, y_val in valid_dataset:
        x_sample = x_val[0].numpy().copy()
        y_sample = y_val[0].numpy().copy()
        x_val, y_val = Variable(torch.tensor(x_val).unsqueeze(1).float()), Variable(torch.tensor(y_val.reshape(y_val.shape[0],-1)).float())
        if torch.cuda.is_available() and use_cuda:
            x_val = x_val.cuda()
            y_val = y_val.cuda()
        output = model(x_val)
        if torch.cuda.is_available() and use_cuda:
            y_out = output.cpu().detach().numpy()[0]
        else:
            y_out = output.detach().numpy()[0]
        loss = criterion(output, y_val)
        cur_valid_loss += loss.item() * x_val.size(0)

    fig, ax = plt.subplots()
    ax.imshow(x_sample, cmap="gray")
    ax.scatter(y_sample[:,0], y_sample[:,1])
    ax.scatter(y_out[0::2], y_out[1::2])
    plt.savefig("epoch%03d.png" % epoch)
    plt.close()

    avg_train_loss = cur_train_loss / len(train_dataset.sampler)
    avg_valid_loss = cur_valid_loss / len(valid_dataset.sampler)

    #     # getting the validation set
    #     # converting the data into GPU format
    #     # if torch.cuda.is_available():
    #     #     x_train = x_train.cuda()
    #     #     y_train = y_train.cuda()
    #     #     x_val = x_val.cuda()
    #     #     y_val = y_val.cuda()

    #     # clearing the Gradients of the model parameters
    #     optimizer.zero_grad()
        
    #     # prediction for training and validation set
    #     output_train = model(x_train)
    #     output_val = model(x_val)

    #     # computing the training and validation loss
    #     # print(output_train.detach().numpy().shape)
    #     # print(y_train.detach().numpy().shape)
    #     loss_train = criterion(output_train, y_train)
    #     loss_val = criterion(output_val, y_val)
    #     train_losses.append(loss_train)
    #     val_losses.append(loss_val)

    #     # computing the updated weights of all the model parameters
    #     loss_train.backward()
    #     optimizer.step()
    #     tr_loss = loss_train.item()
    # if epoch%2 == 0:
    #     # printing the validation loss
    #     print('Epoch : ',epoch+1, '\t', 'loss :', avg_valid_loss)
    print('Epoch : ',epoch+1, '\t', 'loss :', avg_valid_loss)

def main():
    global model, optimizer, criterion

    model = Net()

    use_cuda = True
    use_loading_bar = False

    # print(sum(p.numel() for p in model.parameters() if p.requires_grad))

    image_fnames, data_fnames = face_dataset.find_images()
    images, landmarks_2d, landmarks_3d = face_dataset.load_data(image_fnames, data_fnames, use_loading_bar=use_loading_bar)
    face_dataset.augment_flip(images, landmarks_2d, landmarks_3d)
    images = np.array(images)
    landmarks_2d = np.array(landmarks_2d)
    landmarks_3d = np.array(landmarks_3d)

    X_train, X_val, Y_train, Y_val = train_test_split(images, landmarks_2d, train_size=0.8, test_size=0.2)

    from torch.utils.data import DataLoader, TensorDataset

    BATCH_SIZE = 16

    train_dataset = TensorDataset(torch.tensor(X_train), torch.tensor(Y_train))
    train_dataloader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)

    valid_dataset = TensorDataset(torch.tensor(X_val), torch.tensor(Y_val))
    valid_dataloader = DataLoader(valid_dataset, batch_size=BATCH_SIZE, shuffle=False)


    # defining the optimizer
    optimizer = optim.Adam(model.parameters(), lr=0.07)
    # defining the loss function
    criterion = nn.MSELoss()
    # checking if GPU is available
    if torch.cuda.is_available() and use_cuda:
        model = model.cuda()
        criterion = criterion.cuda()

    n_epochs = 100
    # empty list to store training losses
    train_losses = []
    # empty list to store validation losses
    val_losses = []
    # training the model
    for epoch in range(n_epochs):
        train(epoch, train_dataloader, valid_dataloader, train_losses, val_losses, use_loading_bar=use_loading_bar, use_cuda=use_cuda)

    torch.save(model.state_dict(), "model")


if __name__ == "__main__": 
    main()
