import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from ast import literal_eval
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity
from nltk.stem.snowball import SnowballStemmer
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import wordnet
from surprise import Reader, Dataset, SVD
from surprise.model_selection import cross_validate
from surprise import NormalPredictor
from surprise import KNNBasic
from surprise import Dataset
import tkinter as tk
from tkinter.simpledialog import askstring, askinteger
from tkinter.messagebox import showerror
import time
start_time = time.time()

import warnings; warnings.simplefilter('ignore')


md = pd.read_csv('movies_metadata.csv')
# md.head()


md['genres'] = md['genres'].fillna('[]').apply(literal_eval).apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])


vote_counts = md[md['vote_count'].notnull()]['vote_count'].astype('int')
vote_averages = md[md['vote_average'].notnull()]['vote_average'].astype('int')
C = vote_averages.mean()



m = vote_counts.quantile(0.95)


md['year'] = pd.to_datetime(md['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if x != np.nan else np.nan)


qualified = md[(md['vote_count'] >= m) & (md['vote_count'].notnull()) & (md['vote_average'].notnull())][['title', 'year', 'vote_count', 'vote_average', 'popularity', 'genres']]
qualified['vote_count'] = qualified['vote_count'].astype('int')
qualified['vote_average'] = qualified['vote_average'].astype('int')
qualified.shape



def weighted_rating(x):
	v = x['vote_count']
	R = x['vote_average']
	return (v/(v+m) * R) + (m/(m+v) * C)


qualified['wr'] = qualified.apply(weighted_rating, axis=1)


qualified = qualified.sort_values('wr', ascending=False).head(250)

# qualified.head(15)



s = md.apply(lambda x: pd.Series(x['genres']),axis=1).stack().reset_index(level=1, drop=True)
s.name = 'genre'
gen_md = md.drop('genres', axis=1).join(s)



def build_chart(genre, percentile=0.85):
	for ind in md.index:
     if(md['title'][ind]==movie_name):
      genres=md['genres'][ind]
      genre=genres[0]
      break
	df = gen_md[gen_md['genre'] == genre]
	vote_counts = df[df['vote_count'].notnull()]['vote_count'].astype('int')
	vote_averages = df[df['vote_average'].notnull()]['vote_average'].astype('int')
	C = vote_averages.mean()
	m = vote_counts.quantile(percentile)
	
	qualified = df[(df['vote_count'] >= m) & (df['vote_count'].notnull()) & (df['vote_average'].notnull())][['title', 'year', 'vote_count', 'vote_average', 'popularity']]
	qualified['vote_count'] = qualified['vote_count'].astype('int')
	qualified['vote_average'] = qualified['vote_average'].astype('int')
	
	qualified['wr'] = qualified.apply(lambda x: (x['vote_count']/(x['vote_count']+m) * x['vote_average']) + (m/(m+x['vote_count']) * C), axis=1)
	qualified = qualified.sort_values('wr', ascending=False).head(250)
	
	return qualified.head(10)


print(build_chart('Romance'))


links_small = pd.read_csv('links_small.csv')
links_small = links_small[links_small['tmdbId'].notnull()]['tmdbId'].astype('int')



md = md.drop([19730, 29503, 35587])


md['id'] = md['id'].astype('int')


smd = md[md['id'].isin(links_small)]
# smd.shape


smd['tagline'] = smd['tagline'].fillna('')
smd['description'] = smd['overview'] + smd['tagline']
smd['description'] = smd['description'].fillna('')


tf = TfidfVectorizer(analyzer='word',ngram_range=(1, 2),min_df=0, stop_words='english')
tfidf_matrix = tf.fit_transform(smd['description'])


cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)


cosine_sim[0]



smd = smd.reset_index()
titles = smd['title']
indices = pd.Series(smd.index, index=smd['title'])



def get_recommendations(title):
	idx = indices[title]
	sim_scores = list(enumerate(cosine_sim[idx]))
	sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
	sim_scores = sim_scores[1:31]
	movie_indices = [i[0] for i in sim_scores]
	return titles.iloc[movie_indices].head(10)


# get_recommendations('Iron Man').head(10)



# get_recommendations('The Dark Knight').head(10)



credits = pd.read_csv('credits.csv')
keywords = pd.read_csv('keywords.csv')


keywords['id'] = keywords['id'].astype('int')
credits['id'] = credits['id'].astype('int')
md['id'] = md['id'].astype('int')



md = md.merge(credits, on='id')
md = md.merge(keywords, on='id')


smd = md[md['id'].isin(links_small)]


smd['cast'] = smd['cast'].apply(literal_eval)
smd['crew'] = smd['crew'].apply(literal_eval)
smd['keywords'] = smd['keywords'].apply(literal_eval)
smd['cast_size'] = smd['cast'].apply(lambda x: len(x))
smd['crew_size'] = smd['crew'].apply(lambda x: len(x))


def get_director(x):
	for i in x:
		if i['job'] == 'Director':
			return i['name']
	return np.nan


smd['director'] = smd['crew'].apply(get_director)


smd['cast'] = smd['cast'].apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])
smd['cast'] = smd['cast'].apply(lambda x: x[:3] if len(x) >=3 else x)


smd['keywords'] = smd['keywords'].apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])


smd['cast'] = smd['cast'].apply(lambda x: [str.lower(i.replace(" ", "")) for i in x])



smd['director'] = smd['director'].astype('str').apply(lambda x: str.lower(x.replace(" ", "")))
smd['director'] = smd['director'].apply(lambda x: [x])



s = smd.apply(lambda x: pd.Series(x['keywords']),axis=1).stack().reset_index(level=1, drop=True)
s.name = 'keyword'


s = s.value_counts()
s[:5]


s = s[s > 1]


stemmer = SnowballStemmer('english')
stemmer.stem('dogs')



def filter_keywords(x):
	words = []
	for i in x:
		if i in s:
			words.append(i)
	return words



smd['keywords'] = smd['keywords'].apply(filter_keywords)
smd['keywords'] = smd['keywords'].apply(lambda x: [stemmer.stem(i) for i in x])
smd['keywords'] = smd['keywords'].apply(lambda x: [str.lower(i.replace(" ", "")) for i in x])



smd['soup'] = smd['keywords'] + smd['cast'] + smd['director'] + smd['genres']
smd['soup'] = smd['soup'].apply(lambda x: ' '.join(x))



count = CountVectorizer(analyzer='word',ngram_range=(1, 2),min_df=0, stop_words='english')
count_matrix = count.fit_transform(smd['soup'])



cosine_sim = cosine_similarity(count_matrix, count_matrix)


smd = smd.reset_index()
titles = smd['title']
indices = pd.Series(smd.index, index=smd['title'])


# get_recommendations('The Dark Knight').head(10)


# get_recommendations('Mean Girls').head(10)


def improved_recommendations(title):
	idx = indices[title]
	sim_scores = list(enumerate(cosine_sim[idx]))
	sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
	sim_scores = sim_scores[1:26]
	movie_indices = [i[0] for i in sim_scores]
	
	movies = smd.iloc[movie_indices][['title', 'vote_count', 'vote_average', 'year']]
	vote_counts = movies[movies['vote_count'].notnull()]['vote_count'].astype('int')
	vote_averages = movies[movies['vote_average'].notnull()]['vote_average'].astype('int')
	C = vote_averages.mean()
	m = vote_counts.quantile(0.60)
	qualified = movies[(movies['vote_count'] >= m) & (movies['vote_count'].notnull()) & (movies['vote_average'].notnull())]
	qualified['vote_count'] = qualified['vote_count'].astype('int')
	qualified['vote_average'] = qualified['vote_average'].astype('int')
	qualified['wr'] = qualified.apply(weighted_rating, axis=1)
	qualified = qualified.sort_values('wr', ascending=False).head(10)
	return qualified.head(10)



# improved_recommendations('The Dark Knight')



# improved_recommendations('Mean Girls')



reader = Reader()



ratings = pd.read_csv('ratings_small.csv')
ratings.head()



data = Dataset.load_from_df(ratings[['userId', 'movieId', 'rating']], reader)
cross_validate(NormalPredictor(), data, cv=5)


svd = SVD()
cross_validate(svd, data, measures=['RMSE', 'MAE'], cv=5, verbose=True)



trainset = data.build_full_trainset()
algo = KNNBasic()
algo.fit(trainset)


ratings[ratings['userId'] == 1]



svd.predict(1, 302, 3)


def convert_int(x):
	try:
		return int(x)
	except:
		return np.nan


id_map = pd.read_csv('links_small.csv')[['movieId', 'tmdbId']]
id_map['tmdbId'] = id_map['tmdbId'].apply(convert_int)
id_map.columns = ['movieId', 'id']
id_map = id_map.merge(smd[['title', 'id']], on='id').set_index('title')


indices_map = id_map.set_index('id')



def hybrid(userId, title):
	idx = indices[title]
	tmdbId = id_map.loc[title]['id']
	#print(idx)
	movie_id = id_map.loc[title]['movieId']
	
	sim_scores = list(enumerate(cosine_sim[int(idx)]))
	sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
	sim_scores = sim_scores[1:26]
	movie_indices = [i[0] for i in sim_scores]
	
	movies = smd.iloc[movie_indices][['title', 'vote_count', 'vote_average', 'year', 'id']]
	movies['est'] = movies['id'].apply(lambda x: svd.predict(userId, indices_map.loc[x]['movieId']).est)
	movies = movies.sort_values('est', ascending=False)
	return movies.head(10)

# print(hybrid(500, 'Mean Girls'))
# print("Hello we are in ott.py")
# print("--- %s seconds ---" % (time.time() - start_time))
# hybrid(500, 'Avatar')
# hybrid(1, 'Avatar')

# f = open("hybrid.txt", "w+")
# f.write(hybrid(500, 'Mean Girls'))
# # print(hybrid(500, 'Avatar'))
# f.close()

# fr =open("hybrid.txt", "r") if fr.mode == 'r': pt=fr.read() print
# (pt) fr.close()