# -*- coding: utf-8 -*-
"""Age_Gender.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rF4BbCL4rgr7OQCyS_VuKWeYEj66AptM
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt

from tensorflow.keras.models import Model
from tensorflow.keras.regularizers import l2
from tensorflow.compat.v1 import ConfigProto
from sklearn.preprocessing import LabelBinarizer
from tensorflow.compat.v1 import InteractiveSession
from sklearn.model_selection import train_test_split
from tensorflow.keras.layers import Dense, BatchNormalization
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau

model = tf.keras.applications.resnet.ResNet50(include_top = False, weights = 'imagenet', input_shape = (128,128,3), pooling = 'max')

model.trainable = False

set_trainable = False
for layer in model.layers:
  if layer.name.startswith("conv5"):
    set_trainable = True
  if set_trainable:
    layer.trainable = True
  else:
    layer.trainable = False

x = model.output

bin_classifier = Dense(64, kernel_regularizer = l2(0.05), activation = "tanh")(x)
bin_classifier = BatchNormalization(axis = -1)(bin_classifier)
bin_classifier = Dense(1, kernel_regularizer = l2(0.05), activation = "sigmoid", name = "bin_classifier")(bin_classifier)

reg_head = Dense(64, activation = "tanh")(x)
reg_head = BatchNormalization(axis = -1)(reg_head)
reg_head = Dense(1, name = "reg_head", activation = "linear")(reg_head)

base_model = Model(model.input, [bin_classifier, reg_head])
base_model.summary()

from google.colab import drive
drive.mount('/content/drive')

images = np.load('drive/My Drive/imfdb_dataset/imfdb_images.npy')
gender = np.load('drive/My Drive/imfdb_dataset/imfdb_gender_labels.npy')
age = np.load('drive/My Drive/imfdb_dataset/imfdb_age_labels.npy')

lb = LabelBinarizer()
gender = lb.fit_transform(gender)

age_new = pd.cut(pd.DataFrame(age, columns = ['age']).age, [i for i in range(18, 67, 6)], labels = [i for i in range(8)])
age_new = age_new.to_frame()
age_new = age_new.values.astype('int')

loss_weights = {'reg_head': 1., 'bin_classifier': 8.}
losses = {'reg_head': 'mse', 'bin_classifier': 'binary_crossentropy' }

input_imgen = ImageDataGenerator(rescale = 1./255)

generator = ImageDataGenerator(rescale = 1.)

def generate_data_generator(X, Y1, Y2):
    genX = input_imgen.flow(X, seed = 7, shuffle = False, batch_size = 8)
    genY1 = generator.flow(Y1.reshape(len(Y1), 1, 1, 1), seed = 7, shuffle = False, batch_size = 8)
    genY2 = generator.flow(Y2.reshape(len(Y2), 1, 1, 1), seed = 7, shuffle = False, batch_size = 8)
    while True:
            Xi = genX.next()
            Yi1 = genY1.next()
            Yi2 = genY2.next()
            yield Xi, [Yi1.flatten(), Yi2.flatten()]

base_model.compile(optimizer = tf.keras.optimizers.Adam(lr = 0.001), loss = losses, loss_weights = loss_weights, metrics = ["acc"])

chkpt = ModelCheckpoint(filepath = "model_initial.h5", monitor = 'bin_classifier_acc',\
                        mode = 'max', save_best_only = True, verbose = 1)
early = EarlyStopping(monitor = 'bin_classifier_acc', mode = "max", patience = 5, verbose = 1)
redonplat = ReduceLROnPlateau(monitor = 'bin_classifier_acc', mode = "max", patience = 3, verbose = 2)

callbacks_list = [chkpt, early, redonplat]

base_model.fit(generate_data_generator(images, gender, age_new), steps_per_epoch = len(images)/8, epochs = 10, verbose = 1, callbacks = callbacks_list)