import pandas as pd
import os
import constants



df_films = pd.read_csv(constants.FILMS_LINK)
df_films.to_csv("imdb_backups/films_backup.csv")

df_series = pd.read_csv(constants.SERIES_LINK)
df_series.to_csv("imdb_backups/series_backup.csv")