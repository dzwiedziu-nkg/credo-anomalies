# set the matplotlib backend so figures can be saved in the background
import matplotlib
# import the necessary packages
from dataset_loader import load_dataset
from pyimagesearch.convautoencoder import ConvAutoencoder
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.datasets import mnist
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import numpy as np
import argparse
import random
import pickle
import cv2


matplotlib.use("Agg")


def build_unsupervised_dataset(data, labels, seed=42):

	# grab all indexes of the supplied class label that are *truly*
	# that particular label, then grab the indexes of the image
	# labels that will serve as our "anomalies"
	validIdxs = np.where(labels == 1)[0]
	anomalyIdxs = np.where(labels == 3)[0]

	# randomly shuffle both sets of indexes
	random.seed(seed)
	random.shuffle(validIdxs)
	random.shuffle(anomalyIdxs)

	# compute the total number of anomaly data points to select
	#i = int(len(validIdxs) * contam)
	#anomalyIdxs = anomalyIdxs[:i]

	# use NumPy array indexing to extract both the valid images and
	# "anomlay" images
	validImages = data[validIdxs]
	anomalyImages = data[anomalyIdxs]

	# stack the valid images and anomaly images together to form a
	# single data matrix and then shuffle the rows
	images = np.vstack([validImages, anomalyImages])
	#images = np.vstack([validImages])
	np.random.seed(seed)
	np.random.shuffle(images)

	# return the set of images
	return images, np.vstack([validImages])


def visualize_predictions(decoded, gt, samples=10):
	# initialize our list of output images
	outputs2 = None

	# loop over our number of output samples
	for y in range(0, samples):
		outputs = None
		for x in range(0, samples):
			i = y * samples + x

			# grab the original image and reconstructed image
			original = (gt[i] * 255).astype("uint8")
			recon = (decoded[i] * 255).astype("uint8")

			# stack the original and reconstructed image side-by-side
			output = np.hstack([original, recon])

			# if the outputs array is empty, initialize it as the current
			# side-by-side image display
			if outputs is None:
				outputs = output

			# otherwise, vertically stack the outputs
			else:
				outputs = np.vstack([outputs, output])

		if outputs2 is None:
			outputs2 = outputs

		# otherwise, horizontally stack the outputs
		else:
			outputs2 = np.hstack([outputs2, outputs])

	# return the output images
	return outputs2


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--dataset", type=str, required=True, help="path to output dataset file")
ap.add_argument("-m", "--model", type=str, required=True, help="path to output trained autoencoder")
ap.add_argument("-v", "--vis", type=str, default="recon_vis.png", help="path to output reconstruction visualization file")
ap.add_argument("-p", "--plot", type=str, default="plot.png", help="path to output plot file")
args = vars(ap.parse_args())

# initialize the number of epochs to train for, initial learning rate,
# and batch size
EPOCHS = 100
INIT_LR = 1e-3
BS = 32

# load the MNIST dataset
print("[INFO] loading MNIST dataset...")
#((trainX, trainY), (testX, testY)) = mnist.load_data()
trainX, trainY = load_dataset()

# build our unsupervised dataset of images with a small amount of
# contamination (i.e., anomalies) added into it
print("[INFO] creating unsupervised dataset...")
allImages, images = build_unsupervised_dataset(trainX, trainY)

# add a channel dimension to every image in the dataset, then scale
# the pixel intensities to the range [0, 1]
images = np.expand_dims(images, axis=-1)
images = images.astype("float32") / 255.0

allImages = np.expand_dims(allImages, axis=-1)
allImages = allImages.astype("float32") / 255.0

# construct the training and testing split
(trainX, testX) = train_test_split(images, test_size=0.2, random_state=42)

# construct our convolutional autoencoder
print("[INFO] building autoencoder...")
(encoder, decoder, autoencoder) = ConvAutoencoder.build(60, 60, 1)
opt = Adam(learning_rate=INIT_LR, decay=INIT_LR / EPOCHS)
autoencoder.compile(loss="mse", optimizer=opt)

# train the convolutional autoencoder
H = autoencoder.fit(
	trainX, trainX,
	validation_data=(testX, testX),
	epochs=EPOCHS,
	batch_size=BS)

# use the convolutional autoencoder to make predictions on the
# testing images, construct the visualization, and then save it
# to disk
print("[INFO] making predictions...")
decoded = autoencoder.predict(testX)
vis = visualize_predictions(decoded, testX)
cv2.imwrite(args["vis"], vis)

# construct a plot that plots and saves the training history
N = np.arange(0, EPOCHS)
plt.style.use("ggplot")
plt.figure()
plt.plot(N, H.history["loss"], label="train_loss")
plt.plot(N, H.history["val_loss"], label="val_loss")
plt.title("Training Loss")
plt.xlabel("Epoch #")
plt.ylabel("Loss")
plt.legend(loc="lower left")
plt.savefig(args["plot"])

# serialize the image data to disk
print("[INFO] saving image data...")
f = open(args["dataset"], "wb")
f.write(pickle.dumps(allImages))
f.close()

# serialize the autoencoder model to disk
print("[INFO] saving autoencoder...")
autoencoder.save(args["model"], save_format="h5")

