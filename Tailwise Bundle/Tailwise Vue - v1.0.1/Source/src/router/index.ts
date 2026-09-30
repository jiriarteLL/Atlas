import { createRouter, createWebHistory } from "vue-router";
import Layout from "@/themes";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      component: Layout,
      children: [
        {
          path: "/",
          name: "dashboard-overview-1",
          component: () => import("../pages/DashboardOverview1.vue"),
        },
        {
          path: "/dashboard-overview-2",
          name: "dashboard-overview-2",
          component: () => import("../pages/DashboardOverview2.vue"),
        },
        {
          path: "/dashboard-overview-3",
          name: "dashboard-overview-3",
          component: () => import("../pages/DashboardOverview3.vue"),
        },
        {
          path: "/dashboard-overview-4",
          name: "dashboard-overview-4",
          component: () => import("../pages/DashboardOverview4.vue"),
        },
        {
          path: "/dashboard-overview-5",
          name: "dashboard-overview-5",
          component: () => import("../pages/DashboardOverview5.vue"),
        },
        {
          path: "/dashboard-overview-6",
          name: "dashboard-overview-6",
          component: () => import("../pages/DashboardOverview6.vue"),
        },
        {
          path: "/dashboard-overview-7",
          name: "dashboard-overview-7",
          component: () => import("../pages/DashboardOverview7.vue"),
        },
        {
          path: "/dashboard-overview-8",
          name: "dashboard-overview-8",
          component: () => import("../pages/DashboardOverview8.vue"),
        },
        {
          path: "/users",
          name: "users",
          component: () => import("../pages/Users.vue"),
        },
        {
          path: "/departments",
          name: "departments",
          component: () => import("../pages/Departments.vue"),
        },
        {
          path: "/add-user",
          name: "add-user",
          component: () => import("../pages/AddUser.vue"),
        },
        {
          path: "/profile-overview",
          name: "profile-overview",
          component: () => import("../pages/ProfileOverview.vue"),
        },
        {
          path: "/profile-overview?page=events",
          name: "profile-overview-events",
          component: () => import("../pages/ProfileOverview.vue"),
        },
        {
          path: "/profile-overview?page=achievements",
          name: "profile-overview-achievements",
          component: () => import("../pages/ProfileOverview.vue"),
        },
        {
          path: "/profile-overview?page=contacts",
          name: "profile-overview-contacts",
          component: () => import("../pages/ProfileOverview.vue"),
        },
        {
          path: "/profile-overview?page=default",
          name: "profile-overview-default",
          component: () => import("../pages/ProfileOverview.vue"),
        },
        {
          path: "/settings?page=email-settings",
          name: "settings-email-settings",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=security",
          name: "settings-security",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=preferences",
          name: "settings-preferences",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=two-factor-authentication",
          name: "settings-two-factor-authentication",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=device-history",
          name: "settings-device-history",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=notification-settings",
          name: "settings-notification-settings",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=connected-services",
          name: "settings-connected-services",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=social-media-links",
          name: "settings-social-media-links",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings?page=account-deactivation",
          name: "settings-account-deactivation",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/settings",
          name: "settings",
          component: () => import("../pages/Settings.vue"),
        },
        {
          path: "/billing",
          name: "billing",
          component: () => import("../pages/Billing.vue"),
        },
        {
          path: "/invoice",
          name: "invoice",
          component: () => import("../pages/Invoice.vue"),
        },
        {
          path: "/categories",
          name: "categories",
          component: () => import("../pages/Categories.vue"),
        },
        {
          path: "/add-product",
          name: "add-product",
          component: () => import("../pages/AddProduct.vue"),
        },
        {
          path: "/product-list",
          name: "product-list",
          component: () => import("../pages/ProductList.vue"),
        },
        {
          path: "/product-grid",
          name: "product-grid",
          component: () => import("../pages/ProductGrid.vue"),
        },
        {
          path: "/transaction-list",
          name: "transaction-list",
          component: () => import("../pages/TransactionList.vue"),
        },
        {
          path: "/transaction-detail",
          name: "transaction-detail",
          component: () => import("../pages/TransactionDetail.vue"),
        },
        {
          path: "/seller-list",
          name: "seller-list",
          component: () => import("../pages/SellerList.vue"),
        },
        {
          path: "/seller-detail",
          name: "seller-detail",
          component: () => import("../pages/SellerDetail.vue"),
        },
        {
          path: "/reviews",
          name: "reviews",
          component: () => import("../pages/Reviews.vue"),
        },
        {
          path: "/inbox",
          name: "inbox",
          component: () => import("../pages/Inbox.vue"),
        },
        {
          path: "/file-manager-list",
          name: "file-manager-list",
          component: () => import("../pages/FileManagerList.vue"),
        },
        {
          path: "/file-manager-grid",
          name: "file-manager-grid",
          component: () => import("../pages/FileManagerGrid.vue"),
        },
        {
          path: "/chat",
          name: "chat",
          component: () => import("../pages/Chat.vue"),
        },
        {
          path: "/calendar",
          name: "calendar",
          component: () => import("../pages/Calendar.vue"),
        },
        {
          path: "/point-of-sale",
          name: "point-of-sale",
          component: () => import("../pages/PointOfSale.vue"),
        },
        {
          path: "/creative",
          name: "creative",
          component: () => import("../pages/Creative.vue"),
        },
        {
          path: "/dynamic",
          name: "dynamic",
          component: () => import("../pages/Dynamic.vue"),
        },
        {
          path: "/interactive",
          name: "interactive",
          component: () => import("../pages/Interactive.vue"),
        },
        {
          path: "/regular-table",
          name: "regular-table",
          component: () => import("../pages/RegularTable.vue"),
        },
        {
          path: "/tabulator",
          name: "tabulator",
          component: () => import("../pages/Tabulator.vue"),
        },
        {
          path: "/modal",
          name: "modal",
          component: () => import("../pages/Modal.vue"),
        },
        {
          path: "/slideover",
          name: "slideover",
          component: () => import("../pages/Slideover.vue"),
        },
        {
          path: "/notification",
          name: "notification",
          component: () => import("../pages/Notification.vue"),
        },
        {
          path: "/tab",
          name: "tab",
          component: () => import("../pages/Tab.vue"),
        },
        {
          path: "/accordion",
          name: "accordion",
          component: () => import("../pages/Accordion.vue"),
        },
        {
          path: "/button",
          name: "button",
          component: () => import("../pages/Button.vue"),
        },
        {
          path: "/alert",
          name: "alert",
          component: () => import("../pages/Alert.vue"),
        },
        {
          path: "/progress-bar",
          name: "progress-bar",
          component: () => import("../pages/ProgressBar.vue"),
        },
        {
          path: "/tooltip",
          name: "tooltip",
          component: () => import("../pages/Tooltip.vue"),
        },
        {
          path: "/dropdown",
          name: "dropdown",
          component: () => import("../pages/Dropdown.vue"),
        },
        {
          path: "/typography",
          name: "typography",
          component: () => import("../pages/Typography.vue"),
        },
        {
          path: "/icon",
          name: "icon",
          component: () => import("../pages/Icon.vue"),
        },
        {
          path: "/loading-icon",
          name: "loading-icon",
          component: () => import("../pages/LoadingIcon.vue"),
        },
        {
          path: "/regular-form",
          name: "regular-form",
          component: () => import("../pages/RegularForm.vue"),
        },
        {
          path: "/datepicker",
          name: "datepicker",
          component: () => import("../pages/Datepicker.vue"),
        },
        {
          path: "/tom-select",
          name: "tom-select",
          component: () => import("../pages/TomSelect.vue"),
        },
        {
          path: "/file-upload",
          name: "file-upload",
          component: () => import("../pages/FileUpload.vue"),
        },
        {
          path: "/wysiwyg-editor",
          name: "wysiwyg-editor",
          component: () => import("../pages/WysiwygEditor.vue"),
        },
        {
          path: "/validation",
          name: "validation",
          component: () => import("../pages/Validation.vue"),
        },
        {
          path: "/chart",
          name: "chart",
          component: () => import("../pages/Chart.vue"),
        },
        {
          path: "/slider",
          name: "slider",
          component: () => import("../pages/Slider.vue"),
        },
        {
          path: "/image-zoom",
          name: "image-zoom",
          component: () => import("../pages/ImageZoom.vue"),
        },
      ],
    },
    {
      path: "/landing-page",
      name: "landing-page",
      component: () => import("../pages/LandingPage.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: () => import("../pages/Login.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("../pages/Register.vue"),
    },
  ],
});

export default router;
