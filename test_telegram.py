polling:
  max_item_age_hours: 96
  cleanup_raw_days: 180
  cleanup_runs_days: 30

truth_social:
  enabled: true
  accounts:
    - name: realDonaldTrump
      enabled: true
      profile_url: https://truthsocial.com/@realDonaldTrump
      api_url: https://truthsocial.com/api/v1/accounts/107780257626128497/statuses?exclude_replies=false&with_muted=true&limit=20
      limit: 20

rss:
  enabled: true
  feeds:
    - name: Google News - Trump markets fast
      enabled: true
      limit: 20
      url: https://news.google.com/rss/search?q=Trump%20%28stock%20OR%20stocks%20OR%20market%20OR%20markets%20OR%20Wall%20Street%20OR%20Fed%20OR%20rates%20OR%20tariff%20OR%20tariffs%20OR%20Bitcoin%20OR%20crypto%20OR%20oil%20OR%20gold%29%20when%3A1d&hl=en-US&gl=US&ceid=US:en
    - name: Google News - Trump company CEO mentions
      enabled: true
      limit: 20
      url: https://news.google.com/rss/search?q=Trump%20%28CEO%20OR%20Apple%20OR%20Nvidia%20OR%20Tesla%20OR%20Microsoft%20OR%20Google%20OR%20Meta%20OR%20Amazon%20OR%20Dell%20OR%20JPMorgan%20OR%20Bank%20of%20America%29%20when%3A2d&hl=en-US&gl=US&ceid=US:en
    - name: Google News - Trump X posts market
      enabled: true
      limit: 20
      url: https://news.google.com/rss/search?q=%28Trump%20OR%20Donald%20Trump%29%20%28posted%20OR%20said%20OR%20wrote%29%20%28X%20OR%20Twitter%29%20%28stock%20OR%20market%20OR%20Bitcoin%20OR%20crypto%20OR%20tariff%20OR%20oil%20OR%20Fed%29%20when%3A2d&hl=en-US&gl=US&ceid=US:en
    - name: Google News - Trump live speech markets
      enabled: true
      limit: 20
      url: https://news.google.com/rss/search?q=Trump%20%28live%20OR%20speech%20OR%20interview%20OR%20press%20conference%20OR%20remarks%29%20%28stocks%20OR%20market%20OR%20economy%20OR%20tariffs%20OR%20crypto%20OR%20oil%20OR%20banks%29%20when%3A1d&hl=en-US&gl=US&ceid=US:en
    - name: Google News - Truth Social Trump market
      enabled: true
      limit: 20
      url: https://news.google.com/rss/search?q=Trump%20%22Truth%20Social%22%20%28stock%20OR%20market%20OR%20Bitcoin%20OR%20crypto%20OR%20company%20OR%20CEO%20OR%20tariff%29%20when%3A2d&hl=en-US&gl=US&ceid=US:en
    - name: White House official news
      enabled: true
      limit: 15
      url: https://www.whitehouse.gov/feed/
    - name: White House videos
      enabled: true
      limit: 20
      url: https://www.whitehouse.gov/videos/feed/
    - name: RSBN Trump coverage
      enabled: true
      limit: 20
      url: https://www.rsbnetwork.com/feed/

youtube:
  enabled: true
  transcript_enabled: true
  transcript_max_age_hours: 96
  channels:
    - name: Donald J Trump Official
      enabled: true
      channel_id: UCAql2DyGU2un1Ei2nMYsqOA
      limit: 10
    - name: The White House
      enabled: true
      channel_id: UCYxRlFDqcWM4y7FfpiAN3KQ
      limit: 10
    - name: Right Side Broadcasting Network
      enabled: true
      channel_id: UCHqC-yWZ1kri4YzwRSt6RGQ
      limit: 10

x_api:
  enabled: false
  queries:
    - '(from:realDonaldTrump OR from:TeamTrump OR from:TrumpWarRoom) (stock OR stocks OR market OR Bitcoin OR crypto OR tariff OR tariffs OR oil OR gold OR Fed OR rates OR bank OR economy OR CEO OR company) -is:retweet lang:en'
    - 'Donald Trump (stock OR stocks OR market OR Bitcoin OR crypto OR tariff OR tariffs OR oil OR gold OR Fed OR rates OR bank OR economy OR CEO OR company) -is:retweet lang:en'

live_audio:
  enabled: false
  seconds: 90
  model: tiny.en
  sources:
    - name: RSBN live page
      enabled: true
      url: https://www.youtube.com/@RSBN/live
    - name: The White House live page
      enabled: true
      url: https://www.youtube.com/@WhiteHouse/live
