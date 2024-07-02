Palace is a webgame in the same vein as: Town of Salem, EpicMafia, Mafia.gg

It's uniqueness is the simplicity of the codebase. Combining Django, Websockets, Javascript and jQuery,
the source code is much more compact than that of the mentioned predecessors.

To understand how this was programmed, take a look at the Django-Channels library tutorial,
in which a chatroom is made. This game is an upgraded version of that chatroom. The primary
upgrade is the bot running on the redis server which tracks game-state.
