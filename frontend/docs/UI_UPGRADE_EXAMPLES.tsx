// ============================================
// UI 组件升级 - 前后对比示例
// ============================================

// ╔══════════════════════════════════════════╗
// ║  示例 1: 简单提示消息                     ║
// ╚══════════════════════════════════════════╝

// ❌ 旧方式
alert('操作成功')
alert('创建功能开发中')

// ✅ 新方式
import { toast } from 'sonner'
toast.success('操作成功')
toast.info('创建功能开发中')


// ╔══════════════════════════════════════════╗
// ║  示例 2: 错误提示                         ║
// ╚══════════════════════════════════════════╝

// ❌ 旧方式
try {
  await api.saveData()
  alert('保存成功')
} catch (err) {
  alert(`保存失败: ${err.message}`)
}

// ✅ 新方式
import { toast } from 'sonner'
try {
  await api.saveData()
  toast.success('保存成功')
} catch (err) {
  toast.error(`保存失败: ${err.message}`)
}


// ╔══════════════════════════════════════════╗
// ║  示例 3: 简单确认                         ║
// ╚══════════════════════════════════════════╝

// ❌ 旧方式
if (confirm('确定要继续吗？')) {
  doSomething()
}

// ✅ 新方式
import { useConfirm } from '@/components/ui/confirm-dialog'

const confirm = useConfirm()
const ok = await confirm({
  description: '确定要继续吗？',
})

if (ok) {
  doSomething()
}


// ╔══════════════════════════════════════════╗
// ║  示例 4: 删除确认（危险操作）              ║
// ╚══════════════════════════════════════════╝

// ❌ 旧方式
const handleDelete = async (id: string) => {
  if (!confirm('确定要删除这个采集器吗？')) return
  
  try {
    const response = await api.deleteAdapter(id)
    if (response.success) {
      loadAdapters()
    } else {
      alert(`删除失败: ${response.message}`)
    }
  } catch (err) {
    alert(`删除失败: ${err.message}`)
  }
}

// ✅ 新方式
import { useConfirm } from '@/components/ui/confirm-dialog'
import { toast } from 'sonner'

const confirm = useConfirm()

const handleDelete = async (id: string) => {
  const ok = await confirm({
    title: '删除采集器',
    description: '确定要删除这个采集器吗？此操作无法撤销。',
    confirmText: '删除',
    destructive: true,  // 红色按钮，视觉上强调危险性
  })
  
  if (!ok) return
  
  try {
    const response = await api.deleteAdapter(id)
    if (response.success) {
      toast.success('采集器已删除')
      loadAdapters()
    } else {
      toast.error(`删除失败: ${response.message}`)
    }
  } catch (err) {
    toast.error(`删除失败: ${err.message}`)
  }
}


// ╔══════════════════════════════════════════╗
// ║  示例 5: 批量删除确认                     ║
// ╚══════════════════════════════════════════╝

// ❌ 旧方式
onClick={() => {
  if (confirm(`确定要删除选中的 ${selected.length} 个采集器吗？`)) {
    alert('批量删除功能开发中')
  }
}}

// ✅ 新方式
onClick={async () => {
  const ok = await confirm({
    title: '批量删除采集器',
    description: `确定要删除选中的 ${selected.length} 个采集器吗？此操作无法撤销。`,
    confirmText: '批量删除',
    destructive: true,
  })
  
  if (ok) {
    toast.info('批量删除功能开发中')
  }
}}


// ╔══════════════════════════════════════════╗
// ║  示例 6: 完整的 CRUD 操作流程              ║
// ╚══════════════════════════════════════════╝

// ❌ 旧方式
const handleStart = async (id: string) => {
  try {
    const response = await api.startAdapter(id)
    if (response.success) {
      loadAdapters()  // 无任何反馈
    } else {
      alert(`操作失败: ${response.message}`)
    }
  } catch (err) {
    alert(`操作失败: ${err.message}`)
  }
}

// ✅ 新方式
import { toast } from 'sonner'

const handleStart = async (id: string) => {
  try {
    const response = await api.startAdapter(id)
    if (response.success) {
      toast.success('采集器已启动')  // 清晰的成功反馈
      loadAdapters()
    } else {
      toast.error(`操作失败: ${response.message}`)
    }
  } catch (err) {
    toast.error(`操作失败: ${err.message}`)
  }
}


// ╔══════════════════════════════════════════╗
// ║  改进总结                                 ║
// ╚══════════════════════════════════════════╝

/**
 * 用户体验提升：
 * ✅ 视觉设计更现代化、美观
 * ✅ 有流畅的动画过渡效果
 * ✅ 不会阻塞页面交互
 * ✅ 移动端适配更好
 * ✅ 支持键盘操作（Esc 关闭）
 * ✅ 危险操作有明确的红色视觉提示
 * ✅ Toast 自动消失，不干扰用户
 * ✅ 可以显示多个通知，不会互相覆盖
 * 
 * 开发体验提升：
 * ✅ TypeScript 类型安全
 * ✅ 支持 async/await，代码更清晰
 * ✅ 统一的 API 接口，易于维护
 * ✅ 更容易编写测试
 * ✅ 更容易扩展功能
 * ✅ 与设计系统深度集成
 * 
 * 可访问性提升：
 * ✅ 屏幕阅读器友好
 * ✅ 键盘导航支持
 * ✅ 焦点管理更智能
 * ✅ ARIA 属性完整
 */
