# 🀄 Mahjong Score Analysis Dashboard

A Streamlit-based web application for analyzing, visualizing, and sharing Mahjong game records. 
Upload your CSV data to instantly generate dynamic dashboards, track individual performance, compare play styles, and visualize money flows.

## ✨ Features

* **Instant Dashboarding**: Drag & drop your score CSV files to instantly view stats.
* **Player Comparison**: Head-to-head radar charts and direct stats comparisons.
* **Deep Analytics**: ELO-style ratings, score distributions, and streak tracking.
* **Network & Sankey Charts**: Visualize who plays together often and the flow of points/chips between players.
* **Fun Stats**: Track the longest win streaks, worst losses, and biggest single-day swings.

## 🚀 How to Use

1. Export your Mahjong scores as a CSV file.
2. Open the deployed application URL.
3. Drag and drop your `.csv` file(s) into the sidebar's **Upload Score Files** section.
4. The dashboard will automatically update with your data!

## 🛠️ Local Development

If you want to run this application locally:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/mahjong-dashboard.git
cd mahjong-dashboard

# Install requirements
pip install -r requirements.txt

# Run the app
streamlit run app_en.py
```
