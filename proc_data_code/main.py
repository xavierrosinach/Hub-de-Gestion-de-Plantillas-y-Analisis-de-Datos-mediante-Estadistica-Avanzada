do_scraping = False
do_bronze = False
do_silver = False
do_gold = False

print_info = True

if do_scraping:
    import scraping.main as scraping
    scraping.main(print_info=print_info)

if do_bronze:
    import bronze.main as bronze
    bronze.main(print_info=print_info)

if do_silver:
    import silver.main as silver
    silver.main(print_info=print_info)

if do_gold:
    import gold.main as gold
    gold.main(print_info=print_info)