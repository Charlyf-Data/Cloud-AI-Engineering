from extractor.polars_extract import PolarsExtractor

def main():
    source_path = "data/orders_dataset.csv" 
    extractor = PolarsExtractor(source_path)
    df = extractor.extract_csv(lazy=False)  

    print(df.head())

if __name__ == "__main__":
    main()