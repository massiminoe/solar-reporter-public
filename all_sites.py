import solcast

site_ids = [1]  # only 1 site for this demo

for id in site_ids:
    site = solcast.Site(id=id)

    site.get_actuals()
    site.get_forecast()
    site.create_plots()
    site.send_demo_report()
