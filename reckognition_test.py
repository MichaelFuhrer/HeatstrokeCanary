from HeatstrokeCanary.lib.rekognition_image_detection import RekognitionImage
import boto3


def main():
    rekognition_client = boto3.client('rekognition')
    img = "testimgs/dog01.jpg"

    reko = RekognitionImage.from_file(img, rekognition_client)
    labels = reko.detect_labels(10)
    for label in labels:
        print(f"{label.name}: {str(label.confidence)}")


if __name__ == "__main__":
    main()
