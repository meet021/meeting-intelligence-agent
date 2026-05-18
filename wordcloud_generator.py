import matplotlib.pyplot as plt
from wordcloud import WordCloud
import io
import base64


# Words to ignore in the word cloud
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "ought", "used", "i", "you", "he", "she", "it", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "whose", "when", "where", "why", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "no", "not", "only",
    "same", "so", "than", "too", "very", "just", "about", "also", "up",
    "out", "if", "then", "because", "as", "until", "while", "although",
    "though", "since", "unless", "whether", "after", "before", "during",
    "through", "between", "into", "onto", "upon", "within", "without",
    "along", "following", "across", "behind", "beyond", "plus", "except",
    "going", "get", "got", "go", "let", "like", "well", "back", "even",
    "still", "way", "take", "every", "new", "want", "right", "think",
    "know", "look", "good", "make", "need", "sure", "work", "really",
    "much", "okay", "yes", "yeah", "um", "uh", "now", "here", "there",
    "ll", "re", "ve", "don", "didn", "won", "can", "t", "s", "m"
}


def generate_wordcloud(transcript: str) -> bytes:
    """Generate a word cloud image from transcript and return as bytes."""
    print("💬 Word Cloud Generator running...")

    # Clean the transcript — remove speaker names
    lines = transcript.split('\n')
    clean_text = []
    for line in lines:
        # Remove "Speaker (Role):" prefix
        if ':' in line:
            line = line.split(':', 1)[1]
        clean_text.append(line)

    text = ' '.join(clean_text).strip()

    if not text:
        return None

    try:
        # Generate word cloud
        wc = WordCloud(
            width=800,
            height=400,
            background_color='#0e1117',
            colormap='plasma',
            max_words=100,
            stopwords=STOP_WORDS,
            min_font_size=12,
            max_font_size=80,
            prefer_horizontal=0.7,
            relative_scaling=0.5,
            collocations=False
        )

        wc.generate(text)

        # Convert to bytes
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        fig.patch.set_facecolor('#0e1117')
        plt.tight_layout(pad=0)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight',
                    facecolor='#0e1117', dpi=150)
        plt.close()
        buf.seek(0)

        return buf.getvalue()

    except Exception as e:
        print(f"Word cloud error: {e}")
        return None


def get_top_words(transcript: str, n: int = 15) -> list:
    """Get top N most frequent words from transcript."""
    lines = transcript.split('\n')
    clean_text = []
    for line in lines:
        if ':' in line:
            line = line.split(':', 1)[1]
        clean_text.append(line)

    text = ' '.join(clean_text).lower()

    # Remove punctuation
    for char in '.,!?;:()[]{}"\'-':
        text = text.replace(char, ' ')

    words = text.split()
    word_freq = {}

    for word in words:
        word = word.strip()
        if len(word) > 2 and word not in STOP_WORDS:
            word_freq[word] = word_freq.get(word, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return sorted_words[:n]