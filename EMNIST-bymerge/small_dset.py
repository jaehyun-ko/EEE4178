# -*- coding: utf-8 -*-
"""project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/13dp5XdXoFiYJVcOQzXZ9RLPn4nPw9vib

# Final project of EEE4170
## Classify EMNIST(by merge) Using pytorch 
### 20181485 고재현
"""

import torch
import torchvision
import torch.nn as nn
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
from torch.optim import lr_scheduler
import torch.optim as optim
import numpy as np
from itertools import islice

import time

student_id = '20181485'


def calc_distribution(dataset):
    x = np.concatenate([np.asarray(dataset[i][0]) for i in range(len(dataset))])
    print(x.shape)
    train_mean = np.mean(x)  # , axis=(0, 1,2))
    train_std = np.std(x)  # axis=(0,1,2))
    print(train_mean / 255, train_std / 255)


### train 또는 test dataset에 대하여, num의 수만큼 subplot을 보여주는 함수입니다.
def image_show(dataset, num):
    fig = plt.figure(figsize=(30, 30))

    for i in range(num):
        plt.subplot(1, num, i + 1)
        plt.imshow(dataset[i][0].squeeze())
        plt.title(dataset[i][1])


class TypeData(Dataset):
    '''
  ### Digit일 경우 label로 0을, ###
  ### Letter일 경우 label로 1을 ###
  ### return하는 class입니다. ###
  사용 예시:
  train_data = TypeData(train=True)
  test_data = TypeData(train=False)
    '''

    def __init__(self, train, datatype):
        super(TypeData, self).__init__()
        self.digit = 10
        self.letter = 46
        self.train = train
        self.datatype = datatype

        self.data = torchvision.datasets.EMNIST(root='./',
                                                split=self.datatype,
                                                train=self.train,
                                                transform=transform,  # transforms.ToTensor(),
                                                download=True)

    def __getitem__(self, index):
        if self.datatype == 'bymerge':
            if self.data[index][1] < self.digit:
                label = 0.
            else:
                label = 1.

        elif self.datatype == 'letters':
            label = 1.

        else:  # digits
            label = 0.

        return self.data[index][0], torch.tensor(self.data[index][1]), torch.tensor(label)

    def __len__(self):
        return len(self.data)


transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=(0), std=(0.0013))
    # bymerge-train dataset을 이용해서 구한 mean과 std. mean은 0에 가깝지만 std가 1보다 훨씬 작으니 정규화해주자.
])

datatype = 'bymerge'
train_data = TypeData(train=True, datatype=datatype)  # model 1 train
test_data = TypeData(train=False, datatype=datatype)  # model 1 test

# print((train_data.data))

# calc_distribution(train_data.data)

# set hyperparameter
batch_size = 128
learning_rate = 0.01
num_epoch = 20

train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, drop_last=True)
test_loader = DataLoader(test_data, batch_size=batch_size, shuffle=False, drop_last=True)


class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.layer = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        self.fc_layer1 = nn.Sequential(
            nn.Linear(64 * 7 * 7, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 47),
            nn.BatchNorm1d(47),
            nn.ReLU(),

        )
        self.threshold_layer = nn.Sequential(
            nn.Linear(47, 2),
            nn.ReLU(),
        )

    # def threshold(self, out):
    #     if out[0] < 10:
    #         label = 0.
    #     else:
    #         label = 1.

    def forward(self, x):
        out = self.layer(x)
        out = out.view(batch_size, -1)
        out = self.fc_layer1(out)
        label = self.threshold_layer(out)
        return out, label


class SpinalVGG(nn.Module):
    """
    Based on - https://github.com/kkweon/mnist-competition
    from: https://github.com/ranihorev/Kuzushiji_MNIST/blob/master/KujuMNIST.ipynb
    """

    def two_conv_pool(self, in_channels, f1, f2):
        s = nn.Sequential(
            nn.Conv2d(in_channels, f1, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(f1),
            nn.ReLU(inplace=True),
            nn.Conv2d(f1, f2, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(f2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )
        for m in s.children():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
        return s

    def three_conv_pool(self, in_channels, f1, f2, f3):
        s = nn.Sequential(
            nn.Conv2d(in_channels, f1, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(f1),
            nn.ReLU(inplace=True),
            nn.Conv2d(f1, f2, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(f2),
            nn.ReLU(inplace=True),
            nn.Conv2d(f2, f3, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(f3),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )
        for m in s.children():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
        return s

    def __init__(self, num_classes=47):
        super(SpinalVGG, self).__init__()
        self.l1 = self.two_conv_pool(1, 64, 64)
        self.l2 = self.two_conv_pool(64, 128, 128)
        self.l3 = self.three_conv_pool(128, 256, 256, 256)
        self.l4 = self.three_conv_pool(256, 256, 256, 256)

        self.fc_spinal_layer1 = nn.Sequential(
            nn.Dropout(p=0.5), nn.Linear(Half_width, layer_width),
            nn.BatchNorm1d(layer_width), nn.ReLU(inplace=True), )
        self.fc_spinal_layer2 = nn.Sequential(
            nn.Dropout(p=0.5), nn.Linear(Half_width + layer_width, layer_width),
            nn.BatchNorm1d(layer_width), nn.ReLU(inplace=True), )
        self.fc_spinal_layer3 = nn.Sequential(
            nn.Dropout(p=0.5), nn.Linear(Half_width + layer_width, layer_width),
            nn.BatchNorm1d(layer_width), nn.ReLU(inplace=True), )
        self.fc_spinal_layer4 = nn.Sequential(
            nn.Dropout(p=0.5), nn.Linear(Half_width + layer_width, layer_width),
            nn.BatchNorm1d(layer_width), nn.ReLU(inplace=True), )
        self.fc_out = nn.Sequential(
            nn.Dropout(p=0.5), nn.Linear(layer_width * 4, num_classes), )

    def forward(self, x):
        x = self.l1(x)
        x = self.l2(x)
        x = self.l3(x)
        x = self.l4(x)
        x = x.view(x.size(0), -1)

        x1 = self.fc_spinal_layer1(x[:, 0:Half_width])
        x2 = self.fc_spinal_layer2(torch.cat([x[:, Half_width:2 * Half_width], x1], dim=1))
        x3 = self.fc_spinal_layer3(torch.cat([x[:, 0:Half_width], x2], dim=1))
        x4 = self.fc_spinal_layer4(torch.cat([x[:, Half_width:2 * Half_width], x3], dim=1))

        x = torch.cat([x1, x2], dim=1)
        x = torch.cat([x, x3], dim=1)
        x = torch.cat([x, x4], dim=1)

        x = self.fc_out(x)

        return F.log_softmax(x, dim=1)


class d_CNN(nn.Module):
    def __init__(self):
        super(d_CNN, self).__init__()
        self.layer = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        self.fc_layer = nn.Sequential(
            nn.Linear(64 * 7 * 7, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 10),
        )

    def forward(self, x):
        out = self.layer(x)
        out = out.view(batch_size, -1)
        out = self.fc_layer(out)
        return out


class l_CNN(nn.Module):
    def __init__(self):
        super(l_CNN, self).__init__()
        self.layer = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        self.fc_layer = nn.Sequential(
            nn.Linear(64 * 7 * 7, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 37),
        )

    def forward(self, x):
        out = self.layer(x)
        out = out.view(batch_size, -1)
        out = self.fc_layer(out)
        return out


start = time.time()

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = CNN().to(device)
loss_func = nn.CrossEntropyLoss().to(device)
optimizer = optim.Adam(model.parameters(), lr=learning_rate)
scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.1, patience=1, mode='min', eps=1e-08)
for i in range(num_epoch):

    for n, [image, label1, label2] in islice(enumerate(train_loader), 0, 64):
        x = image.to(device)
        y1_ = label1.to(device=device, dtype=torch.int64)
        y2_ = label2.to(device=device, dtype=torch.int64)

        optimizer.zero_grad()
        output, label = model.forward(x)
        loss1 = (loss_func(output, y1_))
        loss1.backward(retain_graph=True)
        loss2 = (loss_func(label, y2_))
        loss2.backward()
        optimizer.step()
    scheduler.step(loss1)
    # scheduler.step(loss2)
    print('EPOCH: {}, Loss1: {}, Loss2: {}, LR: {}'.format(i, loss1.item(), loss2.item(),
                                                           scheduler.optimizer.state_dict()['param_groups'][0]['lr']))
torch.save(model.state_dict(), './Train_Results/' + 'model_' + student_id + '.pth')
print(time.time() - start)

test_model = CNN().to(device)
checkpoint = torch.load('./Train_Results/' + 'model_' + student_id + '.pth', map_location=device)
test_model.load_state_dict(checkpoint)

correct1 = 0
correct2 = 0
total1 = 0
total2 = 0
test_model.eval()
with torch.no_grad():
    for image, label1, label2 in test_loader:
        x = image.to(device)
        y1_ = label1.to(device)
        y2_ = label2.to(device)
        output1, output2 = test_model.forward(x)
        _, output1_index = torch.max(output1, 1)
        _, output2_index = torch.max(output2, 1)
        total1 += label1.size(0)
        total2 += label2.size(0)
        correct1 += (output1_index == y1_).sum().float()
        correct2 += (output2_index == y2_).sum().float()
    print("model 2 Accuracy of Test Data: {}%".format(100.0 * correct1 / total1))
    print("model 1 Accuracy of Test Data: {}%".format(100.0 * correct2 / total2))