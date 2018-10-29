from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet as wn

from nltk.downloader import nltk

nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
nltk.download('punkt')

#  Convert a Penn Treebank tag to a simplified Wordnet tag
def convertPennTagToWnTag(tag):
    if tag.startswith('N'):
        return wn.NOUN

    if tag.startswith('V'):
        return wn.VERB

    if tag.startswith('J'):
        return wn.ADJ

    if tag.startswith('R'):
        return wn.ADV

    return None

# returns synsets for a pos tagged word
def getSynset(word, tag):
    wordnet_tag = convertPennTagToWnTag(tag)
    if wordnet_tag is None:
        return None

    try:
        return wn.synsets(word, wordnet_tag)[0]  #  Get the most common synset
    except:
        return None

def getPhraseSimilarity(teacherPhrase, studentPhrase):
    # tokenize the phrases and add part-of-speech tags
    teacherPhrase = pos_tag(word_tokenize(teacherPhrase))
    studentPhrase = pos_tag(word_tokenize(studentPhrase))

    # Get the synsets for the pos tagged words
    teacherSynsets = [getSynset(*tagged_word) for tagged_word in teacherPhrase]
    studentSynsets = [getSynset(*tagged_word) for tagged_word in studentPhrase]

    # Filter out the Nones
    teacherSynsets = [ss for ss in teacherSynsets if ss]
    studentSynsets = [ss for ss in studentSynsets if ss]

    score, count = 0.0, 0

    # for each word in the teacher's text/phrase
    for synset in teacherSynsets:
        # checks only whether student synset is empty as student can write wrong answers, assuming that the teacher enters correct text as teacher
        # has to enter correct details to the system without mistakes
        if studentSynsets:
            # get the similarity value of the most similar word in the student's text/phrase
            simList = [synset.path_similarity(ss) for ss in studentSynsets]

            # remove None from list
            simList = [val for val in simList if val is not None]

            if not simList:
                continue

            best_score = max(simList)

            if best_score is not None:
                score = score + best_score
                count = count + 1
        else:
            score = 0
            return score

    if score == 0 or count == 0:
        score = 0
        return score

    # get the average score
    score = score/count
    return score