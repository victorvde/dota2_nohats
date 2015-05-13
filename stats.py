import pstats
p = pstats.Stats('nohats.profile')
p.sort_stats('time').print_stats(30)
