# UI 组件使用指南

本项目已统一使用现代化的弹窗确认和通知系统，不再使用原生的 `alert()` 和 `confirm()`。

## 📦 已实现的组件

### 1. 确认对话框（Confirm Dialog）

基于 Radix UI Dialog 实现的命令式确认对话框，提供与原生 `confirm()` 一致的控制流，但具有更好的用户体验。

#### 使用方法

```tsx
import { useConfirm } from '@/components/ui/confirm-dialog'

function MyComponent() {
  const confirm = useConfirm()

  const handleDelete = async () => {
    const ok = await confirm({
      title: '删除确认',
      description: '确定要删除这个项目吗？此操作无法撤销。',
      confirmText: '删除',
      cancelText: '取消',
      destructive: true, // 红色按钮，用于危险操作
    })
    
    if (ok) {
      // 用户点击了确认
      await deleteItem()
    }
  }

  return <Button onClick={handleDelete}>删除</Button>
}
```

#### 配置选项

```typescript
interface ConfirmOptions {
  title?: string              // 标题，默认「请确认」
  description: React.ReactNode // 描述内容（必填）
  confirmText?: string        // 确认按钮文案，默认「确认」
  cancelText?: string         // 取消按钮文案，默认「取消」
  destructive?: boolean       // 是否使用危险样式（红色），删除操作应设为 true
}
```

#### 特点

- ✅ 返回 Promise<boolean>，与原生 `confirm()` 控制流一致
- ✅ 支持 async/await，代码更清晰
- ✅ 点击确认返回 `true`，点击取消/关闭/按 Esc 返回 `false`
- ✅ 支持危险操作样式（红色按钮）
- ✅ 自动管理焦点和键盘交互
- ✅ 响应式设计，移动端友好

### 2. Toast 通知（Sonner）

基于 Sonner 库实现的优雅 toast 通知系统，支持多种类型和自动消失。

#### 使用方法

```tsx
import { toast } from 'sonner'

function MyComponent() {
  const handleSave = async () => {
    try {
      await saveData()
      toast.success('保存成功')
    } catch (error) {
      toast.error(`保存失败: ${error.message}`)
    }
  }

  return <Button onClick={handleSave}>保存</Button>
}
```

#### Toast 类型

```tsx
// 成功提示（绿色）
toast.success('操作成功')

// 错误提示（红色）
toast.error('操作失败')

// 警告提示（黄色）
toast.warning('请注意')

// 信息提示（蓝色）
toast.info('功能开发中')

// 普通提示
toast('普通消息')
```

#### 高级用法

```tsx
// 带描述的 toast
toast.success('订单提交成功', {
  description: '我们将在 24 小时内处理您的订单'
})

// 带操作按钮的 toast
toast('订单已创建', {
  action: {
    label: '查看',
    onClick: () => console.log('查看订单')
  }
})

// 持久显示（需手动关闭）
toast('重要通知', {
  duration: Infinity,
})

// 自定义持续时间（毫秒）
toast('3秒后消失', {
  duration: 3000,
})
```

## 🚀 已迁移的页面

以下页面已完成从原生 `alert`/`confirm` 到新系统的迁移：

- ✅ `/app/collectors/page.tsx` - 采集器管理页面
- ✅ `/app/scheduler/page.tsx` - 定时任务管理页面

## 📝 迁移指南

### 替换 `alert()`

```tsx
// ❌ 旧方式
alert('操作成功')
alert(`错误: ${error.message}`)

// ✅ 新方式
import { toast } from 'sonner'

toast.success('操作成功')
toast.error(`错误: ${error.message}`)
```

### 替换 `confirm()`

```tsx
// ❌ 旧方式
if (confirm('确定要删除吗？')) {
  deleteItem()
}

// ✅ 新方式
import { useConfirm } from '@/components/ui/confirm-dialog'

const confirm = useConfirm()
const ok = await confirm({
  title: '删除确认',
  description: '确定要删除吗？',
  confirmText: '删除',
  destructive: true,
})

if (ok) {
  deleteItem()
}
```

## 🎨 设计规范

### 何时使用确认对话框

- ✅ 删除操作
- ✅ 不可逆的修改
- ✅ 批量操作
- ✅ 重要的状态变更
- ❌ 简单的信息提示（使用 toast）
- ❌ 表单验证错误（使用表单验证提示）

### 何时使用 Toast

- ✅ 操作成功/失败反馈
- ✅ 后台任务状态更新
- ✅ 非关键性提示
- ✅ "功能开发中"等信息提示
- ❌ 需要用户确认的操作（使用确认对话框）
- ❌ 错误详情和解决方案（使用专门的错误页面）

### 文案建议

#### 确认对话框

- **标题**：简短明确，如"删除确认"、"提交订单"
- **描述**：说明操作后果，如"此操作无法撤销"
- **确认按钮**：使用动词，如"删除"、"提交"、"确认"
- **危险操作**：删除、清空等应设置 `destructive: true`

#### Toast 通知

- **成功**：简洁肯定，如"保存成功"、"已删除"
- **错误**：说明问题，如"保存失败: 网络错误"
- **信息**：友好提示，如"功能开发中"

## 🔧 配置说明

### ConfirmProvider 配置

在 `app/layout.tsx` 中已全局配置：

```tsx
import { ConfirmProvider } from '@/components/ui/confirm-dialog'
import { Toaster } from '@/components/ui/toaster'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <ConfirmProvider>
          {children}
          <Toaster />
        </ConfirmProvider>
      </body>
    </html>
  )
}
```

### Toaster 配置

当前配置（`components/ui/toaster.tsx`）：

```tsx
<Sonner
  position="top-right"  // 位置：右上角
  toastOptions={{
    classNames: {
      // 样式与主题系统集成
      toast: 'group-[.toaster]:bg-card ...',
      // ...
    },
  }}
/>
```

## 📚 参考资源

- [Radix UI Dialog](https://www.radix-ui.com/docs/primitives/components/dialog)
- [Sonner - Toast 库](https://sonner.emilkowal.ski/)
- 参考项目: `/Users/apple/Progame/kiro.rs/admin-ui`

## 🐛 故障排除

### 确认对话框不显示

确保在组件树中包含了 `<ConfirmProvider>`，并且只在 Client Component 中使用：

```tsx
'use client'  // 必须添加此指令

import { useConfirm } from '@/components/ui/confirm-dialog'
```

### Toast 不显示

确保在根布局中包含了 `<Toaster />` 组件。

### 样式问题

确认对话框和 Toast 都使用了项目的主题系统，如果样式异常，检查 Tailwind 配置和 CSS 变量。
