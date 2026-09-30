import { type Icon } from "@/components/Base/Lucide/Lucide.vue";
import { defineStore } from "pinia";

export interface Menu {
  icon: Icon;
  title: string;
  badge?: number;
  pageName?: string;
  subMenu?: Menu[];
  ignore?: boolean;
}

export interface MenuState {
  value: Array<Menu | string>;
}

export const useMenuStore = defineStore("menu", {
  state: (): MenuState => ({
    value: [
      "DASHBOARDS",
      {
        icon: "GaugeCircle",
        pageName: "dashboard-overview-1",
        title: "E-Commerce",
      },
      {
        icon: "ActivitySquare",
        pageName: "dashboard-overview-2",
        title: "CRM",
      },
      {
        icon: "Album",
        pageName: "dashboard-overview-3",
        title: "Hospital",
      },
      {
        icon: "BookMarked",
        pageName: "dashboard-overview-4",
        title: "Factory",
      },
      {
        icon: "HardDrive",
        pageName: "dashboard-overview-5",
        title: "Banking",
      },
      {
        icon: "MousePointerSquare",
        pageName: "dashboard-overview-6",
        title: "Cafe",
      },
      {
        icon: "ShieldHalf",
        pageName: "dashboard-overview-7",
        title: "Crypto",
      },
      {
        icon: "Building",
        pageName: "dashboard-overview-8",
        title: "Hotel",
      },
      "APPS",
      {
        icon: "GanttChartSquare",
        pageName: "inbox",
        title: "Inbox",
        badge: 4,
      },
      {
        icon: "PanelRightClose",
        pageName: "file-manager-list",
        title: "File Manager List",
      },
      {
        icon: "PanelTopClose",
        pageName: "file-manager-grid",
        title: "File Manager Grid",
      },
      {
        icon: "PanelTopClose",
        pageName: "point-of-sale",
        title: "Point of Sale",
      },
      {
        icon: "MailOpen",
        pageName: "chat",
        title: "Chat",
      },
      {
        icon: "CalendarRange",
        pageName: "calendar",
        title: "Calendar",
      },
      "UI WIDGETS",
      {
        icon: "Album",
        pageName: "creative",
        title: "Creative",
      },
      {
        icon: "ActivitySquare",
        pageName: "dynamic",
        title: "Dynamic",
      },
      {
        icon: "Keyboard",
        pageName: "interactive",
        title: "Interactive",
      },
      "USER MANAGEMENT",
      {
        icon: "SquareUser",
        pageName: "users",
        title: "Users",
      },
      {
        icon: "CakeSlice",
        pageName: "departments",
        title: "Departments",
      },
      {
        icon: "PackagePlus",
        pageName: "add-user",
        title: "Add User",
      },
      "PERSONAL DASHBOARD",
      {
        icon: "Presentation",
        pageName: "profile-overview",
        title: "Profile Overview",
      },
      {
        icon: "CalendarRange",
        pageName: "profile-overview-events",
        title: "Events",
      },
      {
        icon: "Medal",
        pageName: "profile-overview-achievements",
        title: "Achievements",
      },
      {
        icon: "TabletSmartphone",
        pageName: "profile-overview-contacts",
        title: "Contacts",
      },
      {
        icon: "Snail",
        pageName: "profile-overview-default",
        title: "Default",
      },
      "GENERAL SETTINGS",
      {
        icon: "Briefcase",
        pageName: "settings",
        title: "Profile Info",
      },
      {
        icon: "MailCheck",
        pageName: "settings-email-settings",
        title: "Email Settings",
      },
      {
        icon: "Fingerprint",
        pageName: "settings-security",
        title: "Security",
      },
      {
        icon: "Radar",
        pageName: "settings-preferences",
        title: "Preferences",
      },
      {
        icon: "DoorOpen",
        pageName: "settings-two-factor-authentication",
        title: "Two-factor Authentication",
      },
      {
        icon: "Keyboard",
        pageName: "settings-device-history",
        title: "Device History",
      },
      {
        icon: "Ticket",
        pageName: "settings-notification-settings",
        title: "Notification Settings",
      },
      {
        icon: "BusFront",
        pageName: "settings-connected-services",
        title: "Connected Services",
      },
      {
        icon: "Podcast",
        pageName: "settings-social-media-links",
        title: "Social Media Links",
      },
      {
        icon: "PackageX",
        pageName: "settings-account-deactivation",
        title: "Account Deactivation",
      },
      "ACCOUNT",
      {
        icon: "PercentSquare",
        pageName: "billing",
        title: "Billing",
      },
      {
        icon: "DatabaseZap",
        pageName: "invoice",
        title: "Invoice",
      },
      "E-COMMERCE",
      {
        icon: "BookMarked",
        pageName: "categories",
        title: "Categories",
      },
      {
        icon: "Compass",
        pageName: "add-product",
        title: "Add Product",
      },
      {
        icon: "Table2",
        pageName: "products",
        title: "Products",
        subMenu: [
          {
            icon: "LayoutPanelTop",
            pageName: "product-list",
            title: "Product List",
          },
          {
            icon: "LayoutPanelLeft",
            pageName: "product-grid",
            title: "Product Grid",
          },
        ],
      },
      {
        icon: "SigmaSquare",
        pageName: "transactions",
        title: "Transactions",
        subMenu: [
          {
            icon: "DivideSquare",
            pageName: "transaction-list",
            title: "Transaction List",
          },
          {
            icon: "PlusSquare",
            pageName: "transaction-detail",
            title: "Transaction Detail",
          },
        ],
      },
      {
        icon: "FileArchive",
        pageName: "sellers",
        title: "Sellers",
        subMenu: [
          {
            icon: "FileImage",
            pageName: "seller-list",
            title: "Seller List",
          },
          {
            icon: "FileBox",
            pageName: "seller-detail",
            title: "Seller Detail",
          },
        ],
      },
      {
        icon: "Goal",
        pageName: "reviews",
        title: "Reviews",
      },
      "AUTHENTICATIONS",
      {
        icon: "BookKey",
        pageName: "login",
        title: "Login",
      },
      {
        icon: "BookLock",
        pageName: "register",
        title: "Register",
      },
      "COMPONENTS",
      {
        icon: "LayoutPanelLeft",
        title: "Table",
        subMenu: [
          {
            icon: "FlipVertical",
            pageName: "regular-table",
            title: "Regular Table",
          },
          {
            icon: "FlipHorizontal",
            pageName: "tabulator",
            title: "Tabulator",
          },
        ],
      },
      {
        icon: "MemoryStick",
        title: "Overlay",
        subMenu: [
          {
            icon: "MenuSquare",
            pageName: "modal",
            title: "Modal",
          },
          {
            icon: "Newspaper",
            pageName: "slideover",
            title: "Slide Over",
          },
          {
            icon: "PanelBottom",
            pageName: "notification",
            title: "Notification",
          },
        ],
      },
      {
        icon: "Package2",
        pageName: "tab",
        title: "Tab",
      },
      {
        icon: "Pocket",
        pageName: "accordion",
        title: "Accordion",
      },
      {
        icon: "PlusSquare",
        pageName: "button",
        title: "Button",
      },
      {
        icon: "Presentation",
        pageName: "alert",
        title: "Alert",
      },
      {
        icon: "ShieldEllipsis",
        pageName: "progress-bar",
        title: "Progress Bar",
      },
      {
        icon: "Clapperboard",
        pageName: "tooltip",
        title: "Tooltip",
      },
      {
        icon: "FlipVertical",
        pageName: "dropdown",
        title: "Dropdown",
      },
      {
        icon: "FileType2",
        pageName: "typography",
        title: "Typography",
      },
      {
        icon: "Aperture",
        pageName: "icon",
        title: "Icon",
      },
      {
        icon: "Droplets",
        pageName: "loading-icon",
        title: "Loading Icon",
      },
      {
        icon: "GalleryHorizontalEnd",
        pageName: "regular-form",
        title: "Regular Form",
      },
      {
        icon: "Microwave",
        pageName: "datepicker",
        title: "Datepicker",
      },
      {
        icon: "Disc3",
        pageName: "tom-select",
        title: "Tom Select",
      },
      {
        icon: "Sandwich",
        pageName: "file-upload",
        title: "File Upload",
      },
      {
        icon: "HopOff",
        pageName: "wysiwyg-editor",
        title: "Wysiwyg Editor",
      },
      {
        icon: "ClipboardType",
        pageName: "validation",
        title: "Validation",
      },
      {
        icon: "PieChart",
        pageName: "chart",
        title: "Chart",
      },
      {
        icon: "KanbanSquare",
        pageName: "slider",
        title: "Slider",
      },
      {
        icon: "Image",
        pageName: "image-zoom",
        title: "Image Zoom",
      },
    ],
  }),
});
