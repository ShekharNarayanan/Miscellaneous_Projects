# nlp_classifier.py

import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

class EmailClassifier:
    def __init__(self):
        self.model = None

    def train(self, emails, labels):
        """
        Train the classifier.
        :param emails: List of email contents.
        :param labels: List of labels corresponding to the emails.
        """
        X_train, X_test, y_train, y_test = train_test_split(emails, labels, test_size=0.2, random_state=42)

        self.model = Pipeline([
            ('tfidf', TfidfVectorizer()),
            ('clf', LogisticRegression())
        ])

        self.model.fit(X_train, y_train)
        predictions = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)
        print(f"Training accuracy: {accuracy:.4f}")

    def predict(self, emails):
        """
        Predict the labels for a list of emails.
        :param emails: List of email contents.
        :return: List of predicted labels.
        """
        if self.model:
            return self.model.predict(emails)
        else:
            raise Exception("Model not trained yet. Please train the model before making predictions.")

    def save_model(self, path):
        """
        Save the trained model to a file.
        :param path: File path to save the model.
        """
        with open(path, 'wb') as file:
            pickle.dump(self.model, file)

    def load_model(self, path):
        """
        Load the trained model from a file.
        :param path: File path to load the model.
        """
        with open(path, 'rb') as file:
            self.model = pickle.load(file)

if __name__ == '__main__':
    # Sample training data
    emails = [
        "Congratulations, we are pleased to invite you to the interview.",
        "We regret to inform you that we will not be proceeding with your application.",
        "Your application has been accepted, welcome aboard!",
        "Thank you for your interest, but we will not be moving forward with your application."
    ]
    labels = ["Accepted", "Rejected", "Accepted", "Rejected"]

    classifier = EmailClassifier()
    classifier.train(emails, labels)
    classifier.save_model('email_classifier.pkl')
