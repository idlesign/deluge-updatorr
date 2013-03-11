Ext.ns('Deluge.ux');

Deluge.plugins.UpdatorrPlugin = Ext.extend(Deluge.Plugin, {

	name: 'Updatorr',

	toggleLabel: {
		true: _('Enable autoupdates'),
		false: _('Disable autoupdates')
	},

	runLabel: {
		true: _('Check updates for selected'),
		false: _('Torrent updates in progress...')
	},

	runAllLabel: {
		true: _('Check for all updates'),
		false: _('Torrent updates in progress...')
	},

	onEnable: function() {

		this.tmSep = deluge.menus.torrent.add({
			xtype: 'menuseparator'
		});
		
		this.tmToggle = deluge.menus.torrent.add({
			text: this.toggleLabel[true],
			handler: this.onToggleClick,
			scope: this
		});
		
		this.tmRun = deluge.menus.torrent.add({
			text: this.runLabel[true],
			handler: this.onRunClick,
			scope: this
		});
		
		this.tmRunAll = deluge.menus.torrent.add({
			text: this.runAllLabel[true],
			handler: this.onRunAllClick,
			scope: this
		});

		deluge.menus.torrent.on('beforeshow', this.torrentMenuToShow, this);

		this.registerTorrentStatus('Updatorr', _('Updatorr'), { colCfg: { hidden: true }});
	},

	onDisable: function() {
		deluge.menus.torrent.remove(this.tmSep);
		deluge.menus.torrent.remove(this.tmToggle);
		deluge.menus.torrent.remove(this.tmRun);
		deluge.menus.torrent.remove(this.tmRunAll);
		deluge.menus.torrent.un('beforeshow', this.torrentMenuToShow, this);
		this.deregisterTorrentStatus('Updatorr');
	},

	torrentMenuToShow: function() {
		var any = false;
		var balance = 0;

		deluge.torrents.getSelections().forEach(function(entry) {
			if (entry.data.Updatorr === "On") { any = true; }
			balance += entry.data.Updatorr === "On" ? 1 : -1;
		});

		this.tmToggle.setText(this.toggleLabel[balance < 0]);
		this.tmRun.setVisible(any);
		
		deluge.client.updatorr.is_walking({success: function(is_walking) {
			this.tmRun.setText(this.runLabel[!is_walking]);
			this.tmRun.setDisabled(is_walking);
			this.tmRunAll.setText(this.runAllLabel[!is_walking]);
			this.tmRunAll.setDisabled(is_walking);
		}, scope: this });
	},

	onRunClick: function(item) {
		deluge.client.updatorr.run_walker( deluge.torrents.getSelectedIds() );
	},

	onRunAllClick: function(item) {
		deluge.client.updatorr.run_walker(true);
	},

	onToggleClick: function(item) {
		var enable = item.text == this.toggleLabel[true];
		var ids = deluge.torrents.getSelectedIds();
		Ext.each(ids, function(id, i) {
			if (ids.length == i +1 ) {
				deluge.client.updatorr.set_items_to_update(id, enable, {
					success: function() {
						deluge.ui.update();
					}
				});
			} else {
				deluge.client.updatorr.set_items_to_update(id, enable);
			}
		});
	}

});


Deluge.registerPlugin('Updatorr', Deluge.plugins.UpdatorrPlugin);