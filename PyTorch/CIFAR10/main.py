'''
This code is for training either modified VGG16 
or a fully connected neural network on the CIFAR10
dataset. Included help functions check accuracy, 
load model, save model, etc. Depending on what 
regularization technique you want to use, set
dropout rate and weight_decay for l2 regularization

'''

import torchvision.models as models
import torch.nn as nn
import torch
import torchvision
import torchvision.transforms as transforms
import sys
from torch.utils.data import DataLoader
from simple_fullynet import fullyNet

# Train CIFAR10 with a CNN or Fully Connected network
train_CNN = True
train_FC = False
assert (train_CNN or train_FC) == 1 # must train on either FC or CNN
        
class CNN_CIFAR10(object):
    def __init__(self):
        self.learning_rate = 0.001
        self.drop_rate = 0.0
        self.weight_decay = 0.0
        self.num_epochs = 100000
        self.batch_size = 64
        self.num_workers = 0
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.dtype =  torch.float32
        self.save_model = False
        self.shuffle = True
        self.pin_memory = True
        self.checkpoint_file = 'checkpoint/CIFAR10_VGG16'
        
    def setup_model(self):
        if train_CNN:
            # Initialize modified VGG16
            model = models.vgg16(pretrained=True)
            model.features[4] = nn.Identity()
            model.features[16] = nn.Identity()
            model.features[23] = nn.Identity()
            model.classifier[6] = nn.Linear(in_features=4096, out_features=10, bias=True)
            model.classifier[2] = nn.Dropout(p=0.0)
            model.classifier[5] = nn.Dropout(p=0.0)
            model.cuda()
            
        elif train_FC:
            # Initialize model
            model = fullyNet(input_size=32*32*3, drop_rate=0.0, init_weights=True)
            model.cuda()
        
        return model
    
    def load_data(self):
        self.transform_train, self.transform_test = self.transformations()
        train_data, validation_data = torch.utils.data.random_split(torchvision.datasets.CIFAR10('./CIFAR10', train=True, transform=self.transform_train), [40000, 10000])                    
        test_data = torchvision.datasets.CIFAR10('./CIFAR10', train=False, transform=self.transform_train)
        
        train_loader = DataLoader(dataset = train_data, batch_size = self.batch_size, num_workers =  self.num_workers)
        validation_loader = DataLoader(dataset = validation_data, batch_size = self.batch_size, num_workers =  self.num_workers)
        test_loader =  DataLoader(dataset = test_data, batch_size = self.batch_size, num_workers = self.num_workers)
        
        return train_loader, validation_loader, test_loader
    
    # Mean, std values previously computed from dataset
    def transformations(self):
        transform_train = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=(0.4914, 0.4822, 0.4465), std=(0.247, 0.243, 0.261)),
            ])
        
        transform_test = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=(0.4914, 0.4822, 0.4465), std=(0.247, 0.243, 0.261)),
            ])

        return transform_train, transform_test
    
    def check_accuracy(self, loader, model):
        num_correct = 0
        num_samples = 0
        model.eval()  # set model to evaluation mode
        
        with torch.no_grad():
            for x, y in loader:
                x = x.to(device=self.device, dtype=self.dtype)  # move to device, e.g. GPU
                y = y.to(device=self.device, dtype=torch.long)
                
                if train_FC:
                    x = x.reshape(x.shape[0], -1)
                    
                scores = model(x)
                _, preds = scores.max(1)
                num_correct += (preds == y).sum()
                num_samples += preds.size(0)
            acc = (float(num_correct) / num_samples) * 100.0
            
            print('Got %d / %d correct (%.2f)' % (num_correct, num_samples, acc))
            
            model.train() # set model back to training mode
            return acc
        
    def save_checkpoint(self, filename, model, optimizer, epoch):
        save_state = {
            'state_dict' : model.state_dict(),
            'epoch' : epoch + 1,
            'optimizer' : optimizer.state_dict(),
                    }
        print()
        print('=> Saving current parameters')
        torch.save(save_state, filename)
    
    def load_model(self, model, optimizer, checkpoint_file):
        checkpoint = torch.load(checkpoint_file)
        model.load_state_dict(checkpoint['state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        
        #Update lr rate and weight decay when loaded model
        for param_group in optimizer.param_groups:
            param_group['lr'] = self.learning_rate
            param_group['weight_decay'] = self.weight_decay
            
        print("=> loaded checkpoint")
    
    def main(self):
        model = self.setup_model()
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.SGD(model.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
        train_loader, validation_loader, test_loader = self.load_data()
        
        # Uncomment if load model
        #self.load_model(model, optimizer, self.checkpoint_file)

        for epoch in range(self.num_epochs):
            # Initialize for measuring running training accuracy
            num_correct, total_checked = 0, 0
            losses = []
            
            for batch_idx, (data, target) in enumerate(train_loader):
                data = data.to(device=self.device, dtype=self.dtype)
                target = target.to(device=self.device, dtype=torch.long)
                
                # If train FullyConnected reshape to make shapes match
                if train_FC:
                    data = data.reshape(data.shape[0], -1)

                #forward prop
                scores = model(data)
                loss = criterion(scores, target)
                losses.append(loss.item())
                
                #backward pass
                optimizer.zero_grad() # Zero gradients from prev. batch
                loss.backward() # Backpropogation
                optimizer.step() # GD step
                
                # For running training accuracy accuracy, NOTE:
                # Running training accuracy is not accurate (and especially not)
                # after a single epoch, but saves on compute
                _, preds = scores.max(1)
                num_correct += (preds == target).sum()
                total_checked += preds.size(0)
                
            
            if self.save_model:
                self.save_checkpoint(self.checkpoint_file, model, optimizer, epoch)
            
            # Print metrics after 1 training epoch
            print(f'Mean loss this epoch: {sum(losses)/len(losses):.4f}')
            print('VALIDATION:')
            self.check_accuracy(validation_loader, model)
            print(f'Accuracy Training: {float(num_correct)/float(total_checked):.4f}')
            print('\n')
            
training = CNN_CIFAR10()
training.main()