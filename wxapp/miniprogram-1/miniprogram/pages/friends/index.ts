import { createListenRoom, getFriendsListening, shareSongCard } from '../../services/api'
import { FEATURED_TRACK } from '../../services/config'
import { firstChar } from '../../utils/display'

type FriendRow = {
  friendId: string
  isOnline: boolean
  name: string
  shortName: string
  status: string
}

type MemberBadge = {
  name: string
  shortName: string
}

Component({
  data: {
    isCreating: false,
    isLoading: false,
    isSharing: false,
    members: [] as MemberBadge[],
    recentFriends: [] as FriendRow[],
    roomMemberCount: 0,
    roomName: '深夜歌单',
    roomSongName: FEATURED_TRACK.songName as string,
    sharePreviewUrl: '',
  },
  lifetimes: {
    attached() {
      this.syncTabBar()
      void this.loadPage()
    },
  },
  pageLifetimes: {
    show() {
      this.syncTabBar()
      void this.loadPage()
    },
  },
  methods: {
    syncTabBar() {
      const tabBar = (this as WechatMiniprogram.Component.TrivialInstance & {
        getTabBar?: () => { setData: (payload: Record<string, unknown>) => void } | null
      }).getTabBar?.()
      tabBar?.setData({ selected: 'pages/friends/index' })
    },
    async loadPage() {
      this.setData({ isLoading: true })

      try {
        const response = await getFriendsListening()
        const members = response.room.members.map((name) => ({
          name,
          shortName: firstChar(name),
        }))
        const recentFriends = response.recentFriends.map((friend) => ({
          friendId: friend.friendId,
          isOnline: friend.isOnline,
          name: friend.nickname || friend.name,
          shortName: firstChar(friend.nickname || friend.name),
          status: friend.status,
        }))

        this.setData({
          members,
          recentFriends,
          roomMemberCount: response.room.memberCount,
          roomName: response.room.roomName,
          roomSongName: response.room.songName,
        })
      } catch (error) {
        wx.showToast({ title: '好友页数据加载失败', icon: 'none' })
      } finally {
        this.setData({ isLoading: false })
      }
    },
    async createRoom() {
      this.setData({ isCreating: true })

      try {
        const room = await createListenRoom(this.data.roomName)
        this.setData({
          roomMemberCount: room.memberCount,
          roomName: room.roomName,
          roomSongName: room.songName,
        })
        wx.showToast({ title: '一起听房间已创建', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '创建房间失败', icon: 'none' })
      } finally {
        this.setData({ isCreating: false })
      }
    },
    async shareCurrentSong() {
      this.setData({ isSharing: true })

      try {
        const result = await shareSongCard({
          artist: FEATURED_TRACK.artist,
          songId: FEATURED_TRACK.songId,
          songName: this.data.roomSongName || FEATURED_TRACK.songName,
          source: FEATURED_TRACK.source,
        })

        this.setData({ sharePreviewUrl: result.previewUrl })
        wx.showToast({ title: '分享卡片已生成', icon: 'success' })
      } catch (error) {
        wx.showToast({ title: '分享生成失败', icon: 'none' })
      } finally {
        this.setData({ isSharing: false })
      }
    },
    async createRoomWithFriend(event: WechatMiniprogram.TouchEvent) {
      const name = String(event.currentTarget.dataset.name || '好友')
      this.setData({ roomName: `${name}的一起听` })
      await this.createRoom()
    },
  },
})
