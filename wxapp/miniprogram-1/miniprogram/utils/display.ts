export function sourceLabel(source: string) {
  if (source === 'qq') {
    return 'QQ 音乐'
  }

  if (source === 'netease') {
    return '网易云音乐'
  }

  return source || '本地音源'
}

export function syncStatusLabel(status: string) {
  if (status === 'synced') {
    return '已同步'
  }

  if (status === 'syncing') {
    return '同步中'
  }

  if (status === 'failed') {
    return '同步异常'
  }

  return '待连接'
}

export function stepStatusLabel(status: string) {
  if (status === 'done') {
    return '已完成'
  }

  if (status === 'doing' || status === 'processing') {
    return '进行中'
  }

  return '等待中'
}

export function firstChar(value: string) {
  return value ? value.slice(0, 1).toUpperCase() : 'M'
}

export function compactTime(value: string) {
  if (!value) {
    return '刚刚'
  }

  if (value.length >= 16) {
    return value.slice(5, 16)
  }

  return value
}
