# 🚀 UI 组件快速参考

## 一分钟上手

### 1️⃣ 确认对话框

```tsx
'use client'
import { useConfirm } from '@/components/ui/confirm-dialog'

export default function MyPage() {
  const confirm = useConfirm()
  
  const handleDelete = async () => {
    const ok = await confirm({
      description: '确定要删除吗？'
    })
    if (ok) {
      // 执行操作
    }
  }
  
  return <button onClick={handleDelete}>删除</button>
}
```

### 2️⃣ Toast 通知

```tsx
import { toast } from 'sonner'

// 成功 ✅
toast.success('操作成功')

// 错误 ❌
toast.error('操作失败')

// 信息 ℹ️
toast.info('功能开发中')

// 警告 ⚠️
toast.warning('请注意')
```

## 常用场景

### 删除确认（推荐）

```tsx
const ok = await confirm({
  title: '删除确认',
  description: '此操作无法撤销，确定要删除吗？',
  confirmText: '删除',
  destructive: true,  // ⚠️ 红色按钮
})
```

### 批量操作确认

```tsx
const ok = await confirm({
  title: '批量删除',
  description: `确定要删除选中的 ${count} 项吗？`,
  confirmText: '批量删除',
  destructive: true,
})
```

### 操作反馈

```tsx
try {
  await api.save()
  toast.success('保存成功')
} catch (err) {
  toast.error(`保存失败: ${err.message}`)
}
```

## API 速查

### useConfirm()

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | string | "请确认" | 对话框标题 |
| `description` | ReactNode | - | 描述内容（必填） |
| `confirmText` | string | "确认" | 确认按钮文案 |
| `cancelText` | string | "取消" | 取消按钮文案 |
| `destructive` | boolean | false | 是否危险操作（红色） |

**返回值**: `Promise<boolean>`

### toast 方法

| 方法 | 说明 | 颜色 |
|------|------|------|
| `toast.success(msg)` | 成功提示 | 绿色 |
| `toast.error(msg)` | 错误提示 | 红色 |
| `toast.info(msg)` | 信息提示 | 蓝色 |
| `toast.warning(msg)` | 警告提示 | 黄色 |
| `toast(msg)` | 普通提示 | 默认 |

## ⚠️ 注意事项

1. **Client Component**: 必须添加 `'use client'` 指令
2. **异步调用**: useConfirm 返回 Promise，需要 await
3. **危险操作**: 删除/清空等操作设置 `destructive: true`
4. **简洁文案**: 标题和按钮文案要简短明确

## ❌ 不要这样做

```tsx
// ❌ 使用原生 alert
alert('操作成功')

// ❌ 使用原生 confirm
if (confirm('确定吗？')) { }

// ❌ 忘记 await
const ok = confirm({ description: '确定吗？' })  // 错误！

// ❌ 在服务端组件中使用
export default function ServerPage() {
  const confirm = useConfirm()  // 错误！
}
```

## ✅ 应该这样做

```tsx
// ✅ 使用 toast
import { toast } from 'sonner'
toast.success('操作成功')

// ✅ 使用 useConfirm
'use client'
import { useConfirm } from '@/components/ui/confirm-dialog'
const confirm = useConfirm()
const ok = await confirm({ description: '确定吗？' })

// ✅ 在客户端组件中使用
'use client'
export default function ClientPage() {
  const confirm = useConfirm()
  // ...
}
```

## 📖 更多信息

- 完整文档: `/frontend/docs/UI_COMPONENTS_GUIDE.md`
- 示例代码: `/frontend/docs/UI_UPGRADE_EXAMPLES.tsx`
- 升级总结: `/frontend/UI_UPGRADE_SUMMARY.md`
