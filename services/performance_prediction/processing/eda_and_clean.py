import argparse
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def rolling_average(group, cols, new_cols):
    group = group.sort_values('date')
    rolling_stats = group[cols].rolling(5, closed='left').mean()
    for col, new_col in zip(cols, new_cols):
        group[new_col] = rolling_stats[col]
    return group.dropna(subset=new_cols)

def clean_data(input_path, output_dir):
    matches = pd.read_csv(input_path)
    matches.reset_index(drop=True, inplace=True)
    matches["date"] = pd.to_datetime(matches["date"])
    matches["venue_code"] = matches["venue"].astype('category').cat.codes
    matches["opp_code"] = matches["opponent"].astype('category').cat.codes
    matches["team"] = matches["team"].astype('category').cat.codes
    matches["hour"] = matches["time"].str.replace(':.+','', regex=True).astype(int)
    matches["day_code"] = matches["date"].dt.dayofweek
    matches["target"] = matches["result"].map({'W': 2, 'D': 1, 'L': 0})

    cols = ['gf', 'ga', 'sh', 'sot', 'dist', 'fk', 'pk', 'pkatt']
    new_cols = [f'{c}_rolling' for c in cols]

    matches_rolling = matches.groupby('team').apply(lambda x: rolling_average(x, cols, new_cols)).reset_index(drop=True)
    matches_rolling = matches_rolling[['date', 'venue_code', 'opp_code', 'day_code', 'hour'] + new_cols + ['team', 'target']]

    opp_rolling = matches_rolling[['team', 'date'] + new_cols].rename(columns={col: f'opp_{col}' for col in new_cols})
    matches_with_opp = matches_rolling.merge(opp_rolling, left_on=['opp_code', 'date'], right_on=['team', 'date'], how='left')
    matches_with_opp = matches_with_opp.drop(columns=['team_y']).rename(columns={'team_x': 'team'})

    columns_to_keep = ['date', 'venue_code', 'opp_code', 'hour', 'day_code', 'team',
                       'gf_rolling', 'ga_rolling', 'sh_rolling', 'sot_rolling',
                       'dist_rolling', 'fk_rolling', 'pk_rolling', 'pkatt_rolling',
                       'opp_gf_rolling', 'opp_ga_rolling', 'opp_sh_rolling',
                       'opp_sot_rolling', 'opp_dist_rolling', 'opp_fk_rolling',
                       'opp_pk_rolling', 'opp_pkatt_rolling', 'target']

    cleaned = matches_with_opp[columns_to_keep]
    cleaned = cleaned.dropna()

    os.makedirs(output_dir, exist_ok=True)
    cleaned.to_csv(os.path.join(output_dir, "cleaned_laliga_matches.csv"), index=False)
    print(f"Cleaned data saved to {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    args = parser.parse_args()

    input_file = os.path.join(args.input_dir, "la_liga_10_seasons.csv")
    clean_data(input_file, args.output_dir)