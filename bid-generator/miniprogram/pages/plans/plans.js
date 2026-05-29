const api = require('../../utils/api');

Page({
  data: {
    plans: [],
    countPacks: [],
    currentTab: 'subscription',
  },

  async onLoad() {
    try {
      const [planRes, packRes] = await Promise.all([
        api.getPlans(),
        api.getCountPacks()
      ]);
      this.setData({
        plans: planRes.data?.subscriptions || [],
        countPacks: packRes.data?.count_packs || []
      });
    } catch (err) {
      console.error('加载套餐失败', err);
    }
  },

  switchTab(e) {
    this.setData({ currentTab: e.currentTarget.dataset.tab });
  },

  async buyPlan(e) {
    const plan = e.currentTarget.dataset.item;
    this.createOrder('subscription', plan.id, plan.name, plan.price);
  },

  async buyPack(e) {
    const pack = e.currentTarget.dataset.item;
    this.createOrder('count_pack', pack.id, pack.name, pack.price);
  },

  async createOrder(orderType, productId, productName, amount) {
    wx.showModal({
      title: '确认购买',
      content: `${productName}\n金额：¥${amount}`,
      success: async (res) => {
        if (!res.confirm) return;

        try {
          const orderRes = await api.createOrder({ order_type: orderType, product_id: productId });
          if (orderRes.status === 'success') {
            const payParams = orderRes.data.pay_params;

            if (payParams._mock) {
              wx.showToast({ title: '支付功能需在正式环境配置微信支付', icon: 'none' });
              return;
            }

            // 调起微信支付
            wx.requestPayment({
              timeStamp: payParams.timeStamp,
              nonceStr: payParams.nonceStr,
              package: payParams.package,
              signType: payParams.signType,
              paySign: payParams.paySign,
              success() {
                wx.showToast({ title: '支付成功！', icon: 'success' });
              },
              fail(err) {
                wx.showToast({ title: '支付取消或失败', icon: 'none' });
              }
            });
          }
        } catch (err) {
          wx.showToast({ title: '下单失败: ' + err.message, icon: 'error' });
        }
      }
    });
  }
});
