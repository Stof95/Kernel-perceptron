#!/usr/bin/env python
# coding: utf-8

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist


class Kernel_perceptron:
    
    def __init__(self, dataset, test_set, train_indices, test_indices, nclasses, kernel_mtx, kernel_param, classification_method='OvA'):
        """
        Initialize perceptron with polynomial or Gaussian kernel, that uses a One-vs-All (OvA) or One-vs-One (OvO) classification method.
        
        -- Input --
        dataset -- training data (LabelledDataset-class, see helper.py)
        test_set -- test data (LabelledDataset-class)
        train_indices -- Lookup indices training set for kernel matrix
        test_indices -- Lookup indices test set for kernel matrix
        nclasses -- number of classification classes
        kernel_mtx -- pre-computed kernel matrix
        classification_method -- 'OvA' or 'OvO' (One-vs-All or One-vs-One)
        """
        
        # data
        self.dataset = dataset
        self.test_set = test_set
        self.nclasses = nclasses
        
        # kernel
        self.kernel_mtx = kernel_mtx
        self.train_indices = np.transpose(train_indices.reshape(1,-1))
        self.test_indices = test_indices
        self.kernel_param = kernel_param
        
        # classification
        self.classification_method = classification_method

        # One-vs-All classification
        if self.classification_method == 'OvA':
            self.classifier = np.zeros((self.nclasses, self.dataset.size))
        
        # One-vs-One classification
        elif self.classification_method == 'OvO':
            k = self.nclasses
            self.classifier = np.zeros((int(k*(k-1)/2), self.dataset.size))
            self.OvO_indices = []
            for idx1 in range(self.nclasses-1):
                for idx2 in range(idx1+1, self.nclasses):
                    self.OvO_indices.append((idx1, idx2))
                    
        
       
    def train(self, max_epochs, epsilon=1e-5):
        
        trainErrors_ = []
        testErrors_ = []
        
        # compute kernel matrix
        K = self.kernel_mtx[self.train_indices, np.transpose(self.train_indices)]
        
        # init values
        prev_train_error = float('inf')
        prev_test_error = float('inf')
        
        for epoch in range(max_epochs):
            
            mistakes = 0
            
            # online learning
            for data_idx, data_point in enumerate(self.dataset.data):

                # compute confidence
                confidence = np.dot(self.classifier, K[data_idx,:])

                # One-vs-All classification
                if self.classification_method == 'OvA':
                    for this_class in range(self.nclasses):
                        if confidence[this_class] > 0 and this_class != self.dataset.labels[data_idx]:
                            mistakes += 1
                            self.classifier[this_class, data_idx] -= 1

                        elif confidence[this_class] <= 0 and this_class == self.dataset.labels[data_idx]:
                            mistakes += 1
                            self.classifier[this_class, data_idx] += 1
                
                # One-vs-One classification                            
                elif self.classification_method == 'OvO':
                    for class_idx, this_pair in enumerate(self.OvO_indices):
                        if this_pair[0] == self.dataset.labels[data_idx] and confidence[class_idx] <= 0:
                            mistakes += 1
                            self.classifier[class_idx, data_idx] += 1
                            
                        if this_pair[1] == self.dataset.labels[data_idx] and confidence[class_idx] > 0:
                            mistakes += 1
                            self.classifier[class_idx, data_idx] -= 1
                            
            # compute train and test errors
            train_error = mistakes/self.dataset.size
            test_error = self.test_error()
            
            # if converged, return misclassification error
            if prev_train_error - train_error  <  epsilon or test_error > prev_test_error + 1e3*epsilon:
                return train_error
            else:
                prev_train_error = train_error
                prev_test_error = test_error
                
#             testErrors_.append(test_error)
#             trainErrors_.append(train_error)
# 
#         plt.plot(np.arange(1, max_epochs+1), trainErrors_, label='train')
#         plt.plot(np.arange(1, max_epochs+1), testErrors_, label='test')
#         plt.legend()
#         plt.title('polynomial kernel, d=%d' %self.kernel_param)
#         plt.show()

        return train_error
                  
    def kernel_output(self, x1, x2):
        """
        Compute kernel matrix. Preferably this is done before initializing this class.
        """
        
        if self.kernel_func == 'polynomial':
            return np.power(np.dot(x1, np.transpose(x2)), self.kernel_param)
        
        if self.kernel_func == 'Gaussian':
            
            # compute distance between each pair of inputs
            xdist = cdist(x1, x2, 'euclidean')            
            
            return np.exp(-self.kernel_param * np.power(xdist, 2))

        
    def predict(self, test_points):
        """
        Predict class of test_point
        """
        
        # lookup kernel from kernel matrix
        K = self.kernel_mtx[self.train_indices, np.transpose(self.test_indices)]
                
        # predict confidences for every class
        confidence = np.dot(self.classifier, K)
        
        # if 1vsAll, return the maximized confidence
        if self.classification_method == 'OvA':
            decisions = np.argmax(confidence, axis=0)
            return decisions
        
        # if 1vs1
        elif self.classification_method == 'OvO':
            
            # calculate all decisions
            confidence = np.transpose(confidence)
            decisions = np.zeros(confidence.shape[0])
            
            # loop through all confidences
            for this_dat in range(confidence.shape[0]):
                
                # initiate current confidence and OvO classifier
                this_confidence = confidence[this_dat]
                OvO_classifier = np.zeros((self.nclasses, 1))
                
                # compare with other OvO calasifiers
                for class_idx, OvO_index in enumerate(self.OvO_indices):
                    
                    # classify
                    if this_confidence[class_idx] > 0:
                        OvO_classifier[OvO_index[0]] += 1
                    else:
                        OvO_classifier[OvO_index[1]] += 1
                        
                 # maximize decision
                decisions[this_dat] = np.argmax(OvO_classifier)
                
            return decisions  
            
    
    def test_error(self):
        """
        Calculate test error
        """     
        predictions = self.predict(self.test_set.data)
                
        mistakes = np.sum(predictions!=self.test_set.labels)

        return mistakes/self.test_set.size

    
    def confusion_matrix(self):
        """
        Generate a confusion matrix
        """
        # count frequency unique classes for normalization
        uniq_vals, counts = np.unique(self.test_set.labels, return_counts=True)
        
        # initialize confusion matrix
        conf_mtx = np.zeros((self.nclasses, self.nclasses))
        
        # predict on the test set
        predictions = self.predict(self.test_set.data)
        
        # loop through each prediction and increment conf_mtx when wrong
        for idx, pred in enumerate(predictions):
            y = self.test_set.labels[idx]
            if pred != y:
                conf_mtx[int(y), int(pred)] += 1
                
        # return normalized (percentage) conf_mtx
        return np.divide(conf_mtx, np.transpose(counts))
    
    
    def count_mistake_vec(self):
        """
        Count mistakes per data instance
        """
        
        mistake_vec = np.zeros(self.kernel_mtx.shape[0])
        
        predictions = self.predict(self.test_set.data)
        
        # loop through all predictions and count mistakes
        for idx, pred in enumerate(predictions):
            if pred != self.test_set.labels[idx]:
                mistake_vec[self.test_indices[idx]] += 1
                
        return mistake_vec
                


