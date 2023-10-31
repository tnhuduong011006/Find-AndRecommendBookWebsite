from langdetect import detect
import spacy
from underthesea import word_tokenize
import joblib
import bson
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from website import connect_db
from bson import ObjectId

db = connect_db()


nlp_vi = spacy.load('vi_core_news_lg')
nlp_en = spacy.load("en_core_web_sm")

# Format = "text" mục đích để có dấu gạch ngang giữa hai từ
# word_tokenize hai lần để tạo list + chuyển văn bản thành chữ thường
''' Hàm tách từ, tiếng việt và tiếng anh'''


def tokenize(string):
    if detect(string) == "vi":
        return word_tokenize(word_tokenize(string, format="text").lower())
#     [token.text.lower() for token in nlp_vi(string)]
    return [token.text.lower() for token in nlp_en(string)]


def preprocess(text):
    if detect(text) == "vi":
        doc = nlp_vi(text)
        no_stopword = [token.text for token in doc if not(
            token.is_punct or token.is_stop or token.is_space)]
    else:
        doc = nlp_en(text)
        # Áp dụng đồng thời bỏ tình thái từ
        no_stopword = [token.lemma_ for token in doc if not(
            token.is_punct or token.is_stop or token.is_space)]

    return no_stopword


def func_merge(text):
    # Đưa vào một chuỗi, kết quả trả về LIST chuỗi đã xử lý
    if text != "":
        try:
            return preprocess(" ".join(tokenize(text)))
        except:
            pass
    return []

def create_tags(df):
    dt = pd.DataFrame()
    # Áp dụng preprocessing cho toàn bộ DataFrame ngoại trừ cột _id
    for col in df.columns:
        dt[col] = df[col].apply(func_merge)
    print(dt)

    dt["Tags"] = dt.TenSach + dt.TacGia + dt.ChuDe + dt.LoaiSach + dt.NXB + dt.STTKe
    dt["Tags"] = dt["Tags"].apply(lambda x: " ".join(x))

    return dt["Tags"]

# Lấy danh sách index của 5 sách có score cao nhất
def get_recommendations(cosine_sim):
    sim_scores = list(enumerate(cosine_sim[0]))  # Danh sách điểm tương đồng, tạo index để truy xuất sau khi sắp xếp giảm dần
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)  # Sắp xếp giảm dần
    min_score = 0.6 * sim_scores[1][1]
    # print("\n\n", sim_scores[0][1], "  ", min_score, "\n\n")
    sim_scores = [i for i in sim_scores if i[1] >= min_score] # Lấy danh sách gợi ý có score >= 70%
    for i in sim_scores[1:]:
        print(i[1])
    book_indices = [i[0] for i in sim_scores[1:]]  # Lấy chỉ số của các sách gợi ý
    
    return book_indices

def total(id):
    # Lấy Tag của sách cần gợi ý
    res = db["books"].find_one({"_id": ObjectId(id)})
    tag = pd.Series(res["Tags"])
    tfidf_vectorizer = joblib.load('website/data/tfidf_vectorizer.pkl')
    # vector shape = (1, 1188)
    vector = tfidf_vectorizer.transform(tag)
    
    # Lấy dữ liệu từ hai trường
    fields_to_retrieve = {"_id": 1, "Tags": 1}
    result = db["books"].find({}, fields_to_retrieve)
    df = pd.DataFrame(result)
    tfidf_matrix = tfidf_vectorizer.transform(df['Tags'])
    
    # Tính toán cosine similarity giữa các sách
    # Cosine_sim là [] lồng [] nên lấy cosine_sim[0] để so sánh kết quả
    cosine_sim = linear_kernel(vector, tfidf_matrix)
    list_idx = get_recommendations(cosine_sim)
    l = df.iloc[list_idx]["_id"].values
    list_id = []
    for i in l:
        list_id.append(str(i))
        
    print(list_id)
    query = {"_id": {"$in": [ObjectId(i) for i in list_id]}}
    results = db["books"].find(query)
   
 
    return results
    