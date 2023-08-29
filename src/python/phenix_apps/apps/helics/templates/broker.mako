<% if cfg['parent'] %>
  helics_broker -f ${cfg['feds']} --broker ${cfg['parent']} --local_interface ${cfg['endpoint']} \
    --loglevel ${cfg['log-level']} --logfile /var/log/helics-broker.log --autorestart &
<% elif cfg['subs'] %>
  helics_broker -f ${cfg['feds']} --ipv4 --subbrokers ${cfg['subs']} \
    --loglevel ${cfg['log-level']} --logfile /var/log/helics-broker.log --autorestart &
<% else %>
  helics_broker -f ${cfg['feds']} --ipv4 --loglevel ${cfg['log-level']} --logfile /var/log/helics-broker.log --autorestart &
<% end %>
